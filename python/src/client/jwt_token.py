import jwt


def verifyToken(token):
    """
    Basic verification if we actually received a JWT token
    """
    return jwt.get_unverified_header(token)
