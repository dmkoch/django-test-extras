from optparse import make_option

from django.conf import settings
from django.db import connections, transaction, DEFAULT_DB_ALIAS
from django.core.management.base import NoArgsCommand, CommandError
from django.core.management.color import no_style
from django.core.management.sql import sql_flush
from django.utils.importlib import import_module


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to flush. '
                'Defaults to the "default" database.'),
    )
    help = ('Deletes all data from the database, and unlike the built in flush command does NOT restore data by executing post-synchronization handlers or loading the initial_data fixture will be re-installed.')

    def handle_noargs(self, **options):
        db = options.get('database')
        connection = connections[db]
        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')

        self.style = no_style()

        sql_list = sql_flush(self.style, connection, only_django=True)

        if interactive:
            confirm = raw_input("""You have requested a flush of the database.
This will IRREVERSIBLY DESTROY all data currently in the %r database,
and return each table to the state it was in after syncdb.
Are you sure you want to do this?

    Type 'yes' to continue, or 'no' to cancel: """ % connection.settings_dict['NAME'])
        else:
            confirm = 'yes'

        if confirm == 'yes':
            try:
                cursor = connection.cursor()
                for sql in sql_list:
                    cursor.execute(sql)
            except Exception, e:
                transaction.rollback_unless_managed(using=db)
                raise CommandError("""Database %s couldn't be flushed. Possible reasons:
  * The database isn't running or isn't configured correctly.
  * At least one of the expected database tables doesn't exist.
  * The SQL was invalid.
Hint: Look at the output of 'django-admin.py sqlflush'. That's the SQL this command wasn't able to run.
The full error: %s""" % (connection.settings_dict['NAME'], e))
            transaction.commit_unless_managed(using=db)

        else:
            print "Flush cancelled."
