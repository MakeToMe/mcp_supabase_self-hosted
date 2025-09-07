"""SQL query validation and sanitization service."""

import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from supabase_mcp_server.core.logging import get_logger

logger = get_logger(__name__)


class QueryRiskLevel(Enum):
    """Risk levels for SQL queries."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"


@dataclass
class ValidationResult:
    """Result of query validation."""
    is_valid: bool
    risk_level: QueryRiskLevel
    issues: List[str]
    warnings: List[str]
    sanitized_query: Optional[str] = None
    requires_confirmation: bool = False


class QueryValidator:
    """SQL query validator and sanitizer."""
    
    def __init__(self):
        """Initialize the query validator."""
        # Dangerous keywords that should be blocked or require confirmation
        self.dangerous_keywords = {
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE',
            'INSERT', 'UPDATE', 'REPLACE', 'MERGE', 'CALL', 'EXEC', 'EXECUTE',
            'SHUTDOWN', 'KILL', 'LOAD', 'OUTFILE', 'DUMPFILE', 'INTO OUTFILE',
            'LOAD_FILE', 'BENCHMARK', 'SLEEP'
        }
        
        # System tables/schemas that should be protected
        self.protected_schemas = {
            'information_schema', 'pg_catalog', 'pg_toast', 'pg_temp',
            'pg_toast_temp', 'public.pg_stat', 'public.pg_settings'
        }
        
        # Allowed read-only operations
        self.safe_keywords = {
            'SELECT', 'WITH', 'EXPLAIN', 'ANALYZE', 'SHOW', 'DESCRIBE', 'DESC'
        }
        
        # SQL injection patterns
        self.injection_patterns = [
            r"(\b(union|or|and)\b.*\b(select|insert|update|delete)\b)",
            r"(;.*--)|(;.*#)|(;.*\/\*)",
            r"(\bor\b.*=.*\bor\b)|(\band\b.*=.*\band\b)",
            r"(char\(|ascii\(|substring\(|length\(|version\()",
            r"(0x[0-9a-f]+)|(\\x[0-9a-f]+)",
            r"(\bwaitfor\b|\bdelay\b)",
        ]
        
        # Compile regex patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
    
    def validate_query(self, query: str, allow_modifications: bool = False) -> ValidationResult:
        """Validate a SQL query for safety and correctness."""
        if not query or not query.strip():
            return ValidationResult(
                is_valid=False,
                risk_level=QueryRiskLevel.SAFE,
                issues=["Query cannot be empty"]
            )
        
        query = query.strip()
        issues = []
        warnings = []
        risk_level = QueryRiskLevel.SAFE
        requires_confirmation = False
        
        # Normalize query for analysis
        normalized_query = self._normalize_query(query)
        
        # Check for SQL injection patterns
        injection_issues = self._check_sql_injection(normalized_query)
        if injection_issues:
            issues.extend(injection_issues)
            risk_level = QueryRiskLevel.DANGEROUS
        
        # Check for dangerous operations
        dangerous_ops = self._check_dangerous_operations(normalized_query)
        if dangerous_ops:
            if allow_modifications:
                warnings.extend(dangerous_ops)
                risk_level = max(risk_level, QueryRiskLevel.HIGH, key=lambda x: x.value)
                requires_confirmation = True
            else:
                issues.extend(dangerous_ops)
                risk_level = QueryRiskLevel.DANGEROUS
        
        # Check for protected schema access
        schema_issues = self._check_protected_schemas(normalized_query)
        if schema_issues:
            warnings.extend(schema_issues)
            risk_level = max(risk_level, QueryRiskLevel.MEDIUM, key=lambda x: x.value)
        
        # Check query complexity
        complexity_warnings = self._check_query_complexity(normalized_query)
        if complexity_warnings:
            warnings.extend(complexity_warnings)
            risk_level = max(risk_level, QueryRiskLevel.LOW, key=lambda x: x.value)
        
        # Sanitize query if possible
        sanitized_query = self._sanitize_query(query) if not issues else None
        
        is_valid = len(issues) == 0
        
        logger.debug(
            "Query validation completed",
            is_valid=is_valid,
            risk_level=risk_level.value,
            issues_count=len(issues),
            warnings_count=len(warnings)
        )
        
        return ValidationResult(
            is_valid=is_valid,
            risk_level=risk_level,
            issues=issues,
            warnings=warnings,
            sanitized_query=sanitized_query,
            requires_confirmation=requires_confirmation
        )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for analysis."""
        # Remove comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        
        return query.strip().upper()
    
    def _check_sql_injection(self, query: str) -> List[str]:
        """Check for SQL injection patterns."""
        issues = []
        
        for pattern in self.compiled_patterns:
            if pattern.search(query):
                issues.append(f"Potential SQL injection detected: {pattern.pattern}")
        
        # Check for suspicious quote usage
        if query.count("'") % 2 != 0:
            issues.append("Unmatched single quotes detected")
        
        # Check for suspicious comment usage
        if '--' in query or '/*' in query:
            issues.append("SQL comments detected - potential injection attempt")
        
        return issues
    
    def _check_dangerous_operations(self, query: str) -> List[str]:
        """Check for dangerous SQL operations."""
        issues = []
        
        # Check for dangerous keywords
        for keyword in self.dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query):
                issues.append(f"Dangerous operation detected: {keyword}")
        
        # Check for multiple statements
        if ';' in query.rstrip(';'):
            issues.append("Multiple SQL statements detected")
        
        # Check for stored procedure calls
        if re.search(r'\b(CALL|EXEC|EXECUTE)\b', query):
            issues.append("Stored procedure execution detected")
        
        return issues
    
    def _check_protected_schemas(self, query: str) -> List[str]:
        """Check for access to protected schemas."""
        warnings = []
        
        for schema in self.protected_schemas:
            if schema.upper() in query:
                warnings.append(f"Access to protected schema detected: {schema}")
        
        return warnings
    
    def _check_query_complexity(self, query: str) -> List[str]:
        """Check for overly complex queries."""
        warnings = []
        
        # Count subqueries
        subquery_count = len(re.findall(r'\(.*SELECT.*\)', query))
        if subquery_count > 3:
            warnings.append(f"High number of subqueries detected: {subquery_count}")
        
        # Count joins
        join_count = len(re.findall(r'\bJOIN\b', query))
        if join_count > 5:
            warnings.append(f"High number of joins detected: {join_count}")
        
        # Check query length
        if len(query) > 5000:
            warnings.append("Very long query detected - may impact performance")
        
        # Check for cartesian products (missing WHERE with multiple tables)
        if 'FROM' in query and ',' in query and 'WHERE' not in query and 'JOIN' not in query:
            warnings.append("Potential cartesian product detected - missing WHERE clause")
        
        return warnings
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query by removing/escaping dangerous elements."""
        # Remove trailing semicolons (except the last one)
        query = query.rstrip(';') + ';' if query.rstrip().endswith(';') else query
        
        # Remove SQL comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def get_safe_query_suggestions(self, query: str) -> List[str]:
        """Get suggestions for making a query safer."""
        suggestions = []
        normalized = self._normalize_query(query)
        
        # Suggest LIMIT for SELECT without LIMIT
        if 'SELECT' in normalized and 'LIMIT' not in normalized:
            suggestions.append("Consider adding a LIMIT clause to prevent large result sets")
        
        # Suggest WHERE clause for UPDATE/DELETE
        if any(op in normalized for op in ['UPDATE', 'DELETE']) and 'WHERE' not in normalized:
            suggestions.append("Add a WHERE clause to limit the scope of the operation")
        
        # Suggest using prepared statements
        if "'" in query:
            suggestions.append("Consider using parameterized queries instead of string literals")
        
        # Suggest EXPLAIN for complex queries
        if any(keyword in normalized for keyword in ['JOIN', 'SUBQUERY', 'UNION']):
            suggestions.append("Use EXPLAIN to analyze query performance")
        
        return suggestions


# Global query validator instance
query_validator = QueryValidator()