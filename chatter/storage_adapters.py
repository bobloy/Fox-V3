from chatterbot.storage import StorageAdapter, SQLStorageAdapter


class MyDumbSQLStorageAdapter(SQLStorageAdapter):
    def __init__(self, **kwargs):
        super(SQLStorageAdapter, self).__init__(**kwargs)

        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker

        self.database_uri = kwargs.get("database_uri", False)

        # None results in a sqlite in-memory database as the default
        if self.database_uri is None:
            self.database_uri = "sqlite://"

        # Create a file database if the database is not a connection string
        if not self.database_uri:
            self.database_uri = "sqlite:///db.sqlite3"

        self.engine = create_engine(self.database_uri, connect_args={"check_same_thread": False})

        if self.database_uri.startswith("sqlite://"):
            from sqlalchemy.engine import Engine
            from sqlalchemy import event

            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
                dbapi_connection.execute("PRAGMA synchronous=NORMAL")

        if not inspect(self.engine).has_table("Statement"):
            self.create_database()

        self.Session = sessionmaker(bind=self.engine, expire_on_commit=True)


class AsyncSQLStorageAdapter(SQLStorageAdapter):
    def __init__(self, **kwargs):
        super(SQLStorageAdapter, self).__init__(**kwargs)

        self.database_uri = kwargs.get("database_uri", False)

        # None results in a sqlite in-memory database as the default
        if self.database_uri is None:
            self.database_uri = "sqlite://"

        # Create a file database if the database is not a connection string
        if not self.database_uri:
            self.database_uri = "sqlite:///db.sqlite3"

    async def initialize(self):
        # from sqlalchemy import create_engine
        from aiomysql.sa import create_engine
        from sqlalchemy.orm import sessionmaker

        self.engine = await create_engine(self.database_uri, convert_unicode=True)

        if self.database_uri.startswith("sqlite://"):
            from sqlalchemy.engine import Engine
            from sqlalchemy import event

            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
                dbapi_connection.execute("PRAGMA synchronous=NORMAL")

        if not self.engine.dialect.has_table(self.engine, "Statement"):
            self.create_database()

        self.Session = sessionmaker(bind=self.engine, expire_on_commit=True)
