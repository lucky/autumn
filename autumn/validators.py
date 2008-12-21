import re

class Validator(object):
    pass
        
class Regex(Validator):        
    def __call__(self, value):
        return bool(self.regex.match(value))
        
class Email(Regex):
    regex = re.compile(r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.(?:[A-Z]{2}|com|org|net|gov|mil|biz|info|mobi|name|aero|jobs|museum)$', re.I)

class Length(Validator):
    def __init__(self, min_length=1, max_length=None):
        if max_length is not None:
            assert max_length >= min_length, "max_length must be greater than or equal to min_length"
        self.min_length = min_length
        self.max_length = max_length
        
    def __call__(self, string):
        l = len(str(string))
        return (l >= self.min_length) and \
               (self.max_length is None or l <= self.max_length)

class Number(Validator):
    def __init__(self, minimum=None, maximum=None):
        if None not in (minimum, maximum):
            assert maximum >= minimum, "maximum must be greater than or equal to minimum"
        self.minimum = minimum
        self.maximum = maximum
        
    def __call__(self, number):
        return isinstance(number, (int, long, float, complex)) and \
               (self.minimum is None or number >= self.minimum) and \
               (self.maximum is None or number <= self.maximum)
               
class ValidatorChain(object):
    def __init__(self, *validators):
        self.validators = validators
    
    def __call__(self, value):
        for validator in self.validators:
            if not validator(value): return False
        return True
