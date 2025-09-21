class Exceptions:
    class CustomException(Exception):
        def __init__(self, add=None): super().__init__(f'{self.__doc__}{f" {add}" if add else ""}')

    class CircularDetected(CustomException):
        "Circular dependency detected!"
    class RuleNotFound(CustomException):
        "Rule not found for:"
    class PrerequisiteNotFound(CustomException):
        "Prerequisite not found!"
    class AtLeastOneConfig(CustomException):
        "At least one config must be present"
    class CommandOrArguments(CustomException):
        "Command or argument must be present"