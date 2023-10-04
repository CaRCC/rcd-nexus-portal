from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from nexus.utils.data import (
    load_capmodel_data,
    load_ipeds_data,
)

IPEDS_DATA = "data/ipeds_2023-02-09.csv"
#QUESTIONS_DATA = "data/capmodel_questions2.json"
#QUESTIONS_DATA = "data/capmodel_questions3.json"
#ASSESSMENTS_DATA = "data/capmodel_2020-21.csv"
ASSESSMENTS_DATA = "data/sensitive/capmodel_2020-22.csv"
#CONTRIBUTORS_DATA = "data/capmodel_2020-21_contributors.csv"
CONTRIBUTORS_DATA = "data/sensitive/capmodel_2020-22_contributors.csv"

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--loadcmds", nargs="+", type=str)

    def handle(self, *args, **options):
        # If no cmds specified, do them all
        if options["loadcmds"]:
            for loadcmd in options["loadcmds"]:
                if loadcmd == "ipeds":
                    load_ipeds_data(IPEDS_DATA)
                elif loadcmd == "data":
                    load_capmodel_data( ASSESSMENTS_DATA, CONTRIBUTORS_DATA )
                else:
                    raise CommandError(
                        'Unknown load command specified to load_nexus_data: "%s"' % loadcmd)
        else:
            load_ipeds_data(IPEDS_DATA)
            load_capmodel_data(ASSESSMENTS_DATA, CONTRIBUTORS_DATA)
