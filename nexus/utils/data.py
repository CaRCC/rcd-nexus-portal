import csv
import json

from django.contrib.auth import get_user_model
from django.utils import timezone

from nexus.models import (
    CapabilitiesAssessment,
    CapabilitiesQuestion,
    Institution,
)
from nexus.models.facings import Facing

DEBUGMODE = False


def load_ipeds_data(path):
    institutions_loaded = 0
    print("Loading institutions...")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if DEBUGMODE:
                print(row)
            institution, created = Institution.objects.get_or_create(
                internet_domain=row["Trimmed URL"],
                defaults={
                    "name": row["Institution Name"],
                    "country": "USA",
                    "state_or_province": row["State Full"],
                    "ipeds_region": row["Region"],
                    "ipeds_sector": row["Sector"],
                    "ipeds_control": row["Pub_Priv"],
                    "ipeds_level": row["Level"],
                    "ipeds_hbcu": row["HBCU"],
                    "ipeds_tcu": row["TCU"],
                    "ipeds_land_grant": row["Land_Grant"],
                    "ipeds_urbanization": row["Urbnzn"],
                    "ipeds_size": row["Size_Cat "]
                    if row["Size_Cat "] != "-2"
                    else None,  # Want to translate -2 to None
                    "carnegie_classification": row["Carneg_Class"],
                    "undergrad_pop": row["# of UG students"].replace(",", "") or 0,
                    "grad_pop": row["# of Grad students"].replace(",", "") or 0,
                    "student_pop": row["Total Students"].replace(",", ""),
                    "research_expenditure": row["Research $ Expend"].replace(",", ""),
                },
            )
            institutions_loaded += 1
            if DEBUGMODE:
                print(institution, created)
    print("Loaded {} institutions.".format(institutions_loaded))


def load_capmodel_questions(path):
    questions_loaded = 0
    print("Skipping loading questions which are in fixtures now...")
    return
    with open(path, "r") as jsonfile:
        data = json.load(jsonfile)

    for row in data:
        facing = Facing.objects.get(slug=row["facing"])
        topic = facing.capmodel_topics.get(slug=row["topic"])

        q, created = CapabilitiesQuestion.objects.get_or_create(
            slug=row['slug'],
            topic=topic,
            defaults={
                "index": topic.questions.count(),
            },
        )
        if "legacy_qid" in row:
            q.attrs["legacy_qid"] = row["legacy_qid"]
        q.contents.get_or_create(text=row["text"], help_text=row["help_text"])
        q.save()
        questions_loaded += 1
    print("Loaded {} questions.".format(questions_loaded))


def load_capmodel_data(path, institution_path):
    """
    Simplify the data with `awk -F, 'BEGIN {OFS=","} $1 ~ /[A-Z]+[0-9]+.[0-9]+/ {print $1,$2,$3,$4,$5,$6,$7,$21,$22,$23,$24,$25}' raw_data.csv`
    """
    assessments_loaded = 0
    print("Loading assessments...")
    user = get_user_model().objects.first()

    institution_ids = dict()
    with open(institution_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for line in reader:
            if DEBUGMODE:
                print(line)
            institution, _ = Institution.objects.get_or_create(
                name=line["IPEDS Institution name"],
                defaults={
                    "internet_domain": line["UnitID"],
                    "list_as_contributor": line["Okay to List publicly"] == "Yes",
                    },
            )
            institution_ids[line["Index"]] = institution

    with open(path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for line in reader:
            if DEBUGMODE:
                print(line)
            institution = institution_ids[line["Inst"]]
            profile, created = institution.profiles.get_or_create(
                year=line["YEAR"], defaults={"created_by": user}
            )
            if created:
                assessment = CapabilitiesAssessment.objects.create(profile=profile)

                assessment.review_status = (
                    CapabilitiesAssessment.ReviewStatusChoices.APPROVED
                )
                assessment.review_time = timezone.now()
                assessment.review_user = user
                assessment.review_note = "Loaded from legacy dataset"
                assessment.save()
                assessments_loaded += 1

            # try:
            if DEBUGMODE:
                print(line)
            answer = profile.capabilities_assessment.answers.get(
                question__attrs__legacy_qid=line["Q ID"]
            )

            # except models.Answer.DoesNotExist:
            #    continue
            # print(line)
            answer.score_deployment = (int(line["DAI"]) - 1) / 4
            answer.score_collaboration = (int(line["MIC"]) - 1) / 4
            answer.score_supportlevel = (int(line["SOL"])- 1) / 4
            answer.priority = line["Pri"] if line["Pri"] != 0 else None
            answer.is_modified = True
            answer.save()

    print("Loaded {} assessments.".format(assessments_loaded))
