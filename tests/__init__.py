import os
import sys

from django.db import connection, connections
from django.test.runner import DiscoverRunner


def asset_path(package, resource):
    return os.path.join(os.path.dirname(sys.modules[package].__file__), resource)


class CleanupTestRunner(DiscoverRunner):
    def teardown_databases(self, old_config, **kwargs):
        if "userdata" in connections:
            connections["userdata"].close()
        connection.close()

        super().teardown_databases(old_config, **kwargs)
