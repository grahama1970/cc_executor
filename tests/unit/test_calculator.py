import pytest
from calculator import Calculator


class TestCalculator:
    """Test suite for Calculator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calc = Calculator()
    
    def test_add(self):
        """Test addition operation"""
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
        assert self.calc.add(0, 0) == 0
        assert self.calc.add(1.5, 2.5) == 4.0
        assert self.calc.add(-5, -3) == -8
    
    def test_subtract(self):
        """Test subtraction operation"""
        assert self.calc.subtract(5, 3) == 2
        assert self.calc.subtract(0, 5) == -5
        assert self.calc.subtract(-3, -5) == 2
        assert self.calc.subtract(10.5, 0.5) == 10.0
        assert self.calc.subtract(0, 0) == 0
    
    def test_multiply(self):
        """Test multiplication operation"""
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(0, 100) == 0
        assert self.calc.multiply(-2, 3) == -6
        assert self.calc.multiply(-2, -3) == 6
        assert self.calc.multiply(2.5, 4) == 10.0
    
    def test_divide(self):
        """Test division operation"""
        assert self.calc.divide(10, 2) == 5
        assert self.calc.divide(7, 2) == 3.5
        assert self.calc.divide(-10, 2) == -5
        assert self.calc.divide(10, -2) == -5
        assert self.calc.divide(0, 5) == 0
    
    def test_divide_by_zero(self):
        """Test division by zero raises exception"""
        with pytest.raises(ZeroDivisionError):
            self.calc.divide(10, 0)
        
        with pytest.raises(ZeroDivisionError):
            self.calc.divide(0, 0)
        
        with pytest.raises(ZeroDivisionError):
            self.calc.divide(-5, 0)