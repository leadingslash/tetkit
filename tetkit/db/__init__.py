def includeme(config):
    config.include("tet.sqlalchemy.simple")
    config.setup_sqlalchemy()
