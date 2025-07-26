class ReadWriteRouter:
    """
    A router to control all database operations on models.
    Routes read operations to 'slave_replica' and write operations to 'default'.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read from 'slave_replica'.
        IMPORTANT: Celery Beat tables must use master to avoid scheduler deadlock.
        """
        if hints.get('instance') and hasattr(hints['instance'], '_state') and hints['instance']._state.db:
             return hints['instance']._state.db
        
        # Force Celery Beat tables to use master database to prevent scheduler deadlock
        if model._meta.app_label == 'django_celery_beat':
            return 'default'
        
        return 'slave_replica'

    def db_for_write(self, model, **hints):
        """
        Attempts to write to the 'default' (master) database.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are allowed on the same db.
        For a simple master/slave setup with replicated data, this is usually fine.
        """
        db_list = ('default', 'slave_replica')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations only run on the 'default' (master) database.
        """
        return db == 'default' 