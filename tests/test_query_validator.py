"""Tests for query validator service."""

import pytest

from supabase_mcp_server.services.query_validator import (
    QueryRiskLevel,
    QueryValidator,
    ValidationResult,
)


class TestQueryValidator:
    """Test QueryValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a query validator instance."""
        return QueryValidator()
    
    def test_validator_creation(self, validator):
        """Test validator creation."""
        assert validator.dangerous_keywords
        assert validator.protected_schemas
        assert validator.safe_keywords
        assert validator.injection_patterns
        assert validator.compiled_patterns
    
    def test_validate_empty_query(self, validator):
        """Test validation of empty query."""
        result = validator.validate_query("")
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.SAFE
        assert "empty" in result.issues[0].lower()
    
    def test_validate_safe_select_query(self, validator):
        """Test validation of safe SELECT query."""
        query = "SELECT id, name FROM users WHERE active = true LIMIT 10"
        result = validator.validate_query(query)
        
        assert result.is_valid is True
        assert result.risk_level == QueryRiskLevel.SAFE
        assert len(result.issues) == 0
        assert result.sanitized_query is not None
    
    def test_validate_dangerous_drop_query(self, validator):
        """Test validation of dangerous DROP query."""
        query = "DROP TABLE users"
        result = validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("DROP" in issue for issue in result.issues)
    
    def test_validate_dangerous_delete_query(self, validator):
        """Test validation of dangerous DELETE query."""
        query = "DELETE FROM users"
        result = validator.validate_query(query, allow_modifications=True)
        
        assert result.is_valid is True  # Valid when modifications allowed
        assert result.risk_level == QueryRiskLevel.HIGH
        assert result.requires_confirmation is True
        assert any("DELETE" in warning for warning in result.warnings)
    
    def test_validate_sql_injection_attempt(self, validator):
        """Test validation of SQL injection attempt."""
        query = "SELECT * FROM users WHERE id = 1 OR 1=1 --"
        result = validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("injection" in issue.lower() for issue in result.issues)
    
    def test_validate_multiple_statements(self, validator):
        """Test validation of multiple statements."""
        query = "SELECT * FROM users; DROP TABLE users;"
        result = validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("Multiple" in issue for issue in result.issues)
    
    def test_validate_protected_schema_access(self, validator):
        """Test validation of protected schema access."""
        query = "SELECT * FROM information_schema.tables"
        result = validator.validate_query(query)
        
        assert result.is_valid is True  # Valid but with warnings
        assert result.risk_level == QueryRiskLevel.MEDIUM
        assert any("protected schema" in warning.lower() for warning in result.warnings)
    
    def test_validate_complex_query(self, validator):
        """Test validation of complex query."""
        query = """
        SELECT u.id, u.name, p.title
        FROM users u
        JOIN posts p ON u.id = p.user_id
        JOIN comments c ON p.id = c.post_id
        JOIN likes l ON c.id = l.comment_id
        JOIN shares s ON p.id = s.post_id
        JOIN follows f ON u.id = f.user_id
        WHERE u.active = true
        """
        result = validator.validate_query(query)
        
        assert result.is_valid is True
        assert result.risk_level == QueryRiskLevel.LOW
        assert any("joins" in warning.lower() for warning in result.warnings)
    
    def test_validate_query_with_comments(self, validator):
        """Test validation of query with comments."""
        query = "SELECT * FROM users -- This is a comment"
        result = validator.validate_query(query)
        
        assert result.is_valid is False  # Comments are considered suspicious
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("comment" in issue.lower() for issue in result.issues)
    
    def test_validate_unmatched_quotes(self, validator):
        """Test validation of query with unmatched quotes."""
        query = "SELECT * FROM users WHERE name = 'John"
        result = validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("quote" in issue.lower() for issue in result.issues)
    
    def test_validate_stored_procedure_call(self, validator):
        """Test validation of stored procedure call."""
        query = "CALL get_user_stats(1)"
        result = validator.validate_query(query)
        
        assert result.is_valid is False
        assert result.risk_level == QueryRiskLevel.DANGEROUS
        assert any("CALL" in issue for issue in result.issues)
    
    def test_normalize_query(self, validator):
        """Test query normalization."""
        query = """
        SELECT   *   FROM   users   
        -- This is a comment
        /* Another comment */
        WHERE   id   =   1
        """
        normalized = validator._normalize_query(query)
        
        assert "SELECT * FROM USERS WHERE ID = 1" == normalized
        assert "--" not in normalized
        assert "/*" not in normalized
    
    def test_check_sql_injection_patterns(self, validator):
        """Test SQL injection pattern detection."""
        test_cases = [
            ("SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords", True),
            ("SELECT * FROM users WHERE name = 'admin' OR '1'='1'", True),
            ("SELECT * FROM users WHERE id = 1; DROP TABLE users;", True),
            ("SELECT * FROM users WHERE id = 1", False),
        ]
        
        for query, should_detect in test_cases:
            issues = validator._check_sql_injection(query.upper())
            if should_detect:
                assert len(issues) > 0, f"Should detect injection in: {query}"
            else:
                assert len(issues) == 0, f"Should not detect injection in: {query}"
    
    def test_check_dangerous_operations(self, validator):
        """Test dangerous operation detection."""
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM users",
            "UPDATE users SET password = 'hacked'",
            "INSERT INTO users VALUES (1, 'hacker')",
            "TRUNCATE TABLE users",
            "ALTER TABLE users ADD COLUMN hacked TEXT",
        ]
        
        for query in dangerous_queries:
            issues = validator._check_dangerous_operations(query.upper())
            assert len(issues) > 0, f"Should detect dangerous operation in: {query}"
    
    def test_check_protected_schemas(self, validator):
        """Test protected schema detection."""
        protected_queries = [
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM pg_catalog.pg_tables",
            "SELECT * FROM public.pg_stat_activity",
        ]
        
        for query in protected_queries:
            warnings = validator._check_protected_schemas(query.upper())
            assert len(warnings) > 0, f"Should detect protected schema in: {query}"
    
    def test_check_query_complexity(self, validator):
        """Test query complexity detection."""
        # Test high number of joins
        complex_query = "SELECT * FROM t1 " + " ".join([f"JOIN t{i} ON t1.id = t{i}.id" for i in range(2, 8)])
        warnings = validator._check_query_complexity(complex_query.upper())
        assert any("joins" in warning.lower() for warning in warnings)
        
        # Test long query
        long_query = "SELECT " + ", ".join([f"column_{i}" for i in range(200)]) + " FROM users"
        warnings = validator._check_query_complexity(long_query.upper())
        assert any("long query" in warning.lower() for warning in warnings)
        
        # Test potential cartesian product
        cartesian_query = "SELECT * FROM users, posts, comments"
        warnings = validator._check_query_complexity(cartesian_query.upper())
        assert any("cartesian" in warning.lower() for warning in warnings)
    
    def test_sanitize_query(self, validator):
        """Test query sanitization."""
        query = """
        SELECT * FROM users -- comment
        /* another comment */
        WHERE id = 1;;;
        """
        sanitized = validator._sanitize_query(query)
        
        assert "--" not in sanitized
        assert "/*" not in sanitized
        assert sanitized.count(";") <= 1
        assert "SELECT * FROM users WHERE id = 1;" == sanitized
    
    def test_get_safe_query_suggestions(self, validator):
        """Test safe query suggestions."""
        # Test SELECT without LIMIT
        query = "SELECT * FROM users"
        suggestions = validator.get_safe_query_suggestions(query)
        assert any("LIMIT" in suggestion for suggestion in suggestions)
        
        # Test UPDATE without WHERE
        query = "UPDATE users SET active = false"
        suggestions = validator.get_safe_query_suggestions(query)
        assert any("WHERE" in suggestion for suggestion in suggestions)
        
        # Test query with string literals
        query = "SELECT * FROM users WHERE name = 'John'"
        suggestions = validator.get_safe_query_suggestions(query)
        assert any("parameterized" in suggestion for suggestion in suggestions)
        
        # Test complex query
        query = "SELECT * FROM users u JOIN posts p ON u.id = p.user_id"
        suggestions = validator.get_safe_query_suggestions(query)
        assert any("EXPLAIN" in suggestion for suggestion in suggestions)
    
    def test_risk_level_ordering(self):
        """Test that risk levels can be compared."""
        assert QueryRiskLevel.SAFE.value < QueryRiskLevel.LOW.value
        assert QueryRiskLevel.LOW.value < QueryRiskLevel.MEDIUM.value
        assert QueryRiskLevel.MEDIUM.value < QueryRiskLevel.HIGH.value
        assert QueryRiskLevel.HIGH.value < QueryRiskLevel.DANGEROUS.value


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            is_valid=True,
            risk_level=QueryRiskLevel.LOW,
            issues=[],
            warnings=["Test warning"],
            sanitized_query="SELECT * FROM users;",
            requires_confirmation=False
        )
        
        assert result.is_valid is True
        assert result.risk_level == QueryRiskLevel.LOW
        assert len(result.issues) == 0
        assert len(result.warnings) == 1
        assert result.sanitized_query == "SELECT * FROM users;"
        assert result.requires_confirmation is False