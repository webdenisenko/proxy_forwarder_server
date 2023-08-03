import random
import string


def random_str(length=6):
    """ Generate random string """
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase) for _ in range(length))