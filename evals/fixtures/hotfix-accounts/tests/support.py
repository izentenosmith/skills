from boxwise.db import open_db


def fresh_db():
    return open_db(":memory:")
