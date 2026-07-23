import csv
import json
import re
from datetime import datetime

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from nexus.models import (
    CapabilitiesAssessment,
    CapabilitiesTopic,
    CapabilitiesQuestion,
    Institution,
)
from nexus.models.facings import Facing

DEBUGMODE = False
topicQIDpattern = re.compile(r'^[A-Z]{1,2}\d{1,2}$')
questionQIDpattern = re.compile(r'^[A-Z]{1,2}\d{1,2}\.\d{1,2}$')


def initial_load_ipeds_data(path):
    institutions_loaded = 0
    print("Loading institutions...")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if DEBUGMODE:
                print(row)
            try:
                institution, created = Institution.objects.get_or_create(
                    ipeds_unitid=row["UnitID"],
                    defaults={
                        "name": row["Institution Name"],
                        "internet_domain":row["Trimmed URL"],
                        "country": "USA",
                        "state_or_province": row["State Full"],
                        "ipeds_unitid": row["UnitID"],
                        "ipeds_region": row["Region"],
                        "ipeds_sector": row["Sector"],
                        "ipeds_control": row["Pub_Priv"],
                        "ipeds_level": row["Level"],
                        "ipeds_hbcu": row["HBCU"],
                        "ipeds_pbi": row["PBI"],
                        "ipeds_tcu": row["TCU"],
                        "ipeds_hsi": row["HSI"],
                        "ipeds_aanapisi_annh": row["AANAPISI_ANNH"],
                        "ipeds_msi": row["MSI"],
                        "ipeds_epscor": row["EPSCoR"],
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
            except IntegrityError as e:
                print(e, row)
                continue
            institutions_loaded += 1
            if DEBUGMODE:
                print(institution, created)
    print("Loaded {} institutions.".format(institutions_loaded))


def update_ipeds_data(path):
    institutions_loaded = 0
    print("Updating institutions...")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if DEBUGMODE:
                print(row)
            try:
                institution, created = Institution.objects.update_or_create(
                    ipeds_unitid=row["UnitID"],
                    defaults={
                        "name": row["Institution Name"],
                        "internet_domain":row["Trimmed URL"],
                        "country": "USA",
                        "state_or_province": row["State Full"],
                        "ipeds_unitid": row["UnitID"],
                        "ipeds_region": row["Region"],
                        "ipeds_sector": row["Sector"],
                        "ipeds_control": row["Pub_Priv"],
                        "ipeds_level": row["Level"],
                        "ipeds_hbcu": row["HBCU"],
                        "ipeds_pbi": row["PBI"],
                        "ipeds_tcu": row["TCU"],
                        "ipeds_hsi": row["HSI"],
                        "ipeds_aanapisi_annh": row["AANAPISI_ANNH"],
                        "ipeds_msi": row["MSI"],
                        "ipeds_epscor": row["EPSCoR"],
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
            except IntegrityError as e:
                print(e)
                continue

def link_ipeds_unitids(path):
    print("Updating institutions...")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if DEBUGMODE:
                print(row)
            try:
                institution = Institution.objects.get(
                    internet_domain=row["Trimmed URL"],
                )
            except Institution.DoesNotExist:
                try:
                    institution = Institution.objects.get(
                        name=row["Institution Name"],
                        country="USA",
                        state_or_province=row["State Full"],
                    )
                except Institution.DoesNotExist:
                    print("Could not find institution for {}".format(row))
                    continue

            institution.ipeds_unitid = row["UnitID"]
            institution.save()


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

topic_QID_to_slug_mapping = {
    "R2" : "outreach",
    "R1" : "staffing",
    "R3" : "consulting",
    "R4" : "lifecycle",
    "D1" : "creation",
    "D2" : "discovery",
    "D3" : "analysis",
    "D4" : "visualization",
    "D5" : "curation",
    "D6" : "policy",
    "D7" : "security",
    "SW1" : "management",
    "SW2" : "development",
    "SW3" : "optimization",
    "SW4" : "workflow",
    "SW5" : "portability",
    "SW6" : "access",
    "SW7" : "physical_specimens",
    "SY1" : "infrastructure",
    "SY2" : "compute",
    "SY3" : "storage",
    "SY4" : "network",
    "SY5" : "specialized",
    "SY6" : "software",
    "SY7" : "monitoring",
    "SY8" : "recordkeeping",
    "SY9" : "documentation",
    "SY10" : "planning",
    "SY11" : "security",
    "SP1" : "alignment",
    "SP2" : "culture",
    "SP3" : "funding",
    "SP4" : "partnerships",
    "SP5" : "professionalization",
    "SP6" : "diversity",    
}

def getSlugForTopicQID(qid):
    return topic_QID_to_slug_mapping.get(qid)

def getFacingSlugForTopicQID(qid):
    facingslug = None
    if qid.startswith("R"):
        facingslug = "researcher"
    elif qid.startswith("D"):
        facingslug = "data"
    elif qid.startswith("SW"):
        facingslug = "software"
    elif qid.startswith("SY"):
        facingslug = "systems"
    elif qid.startswith("SP"):
        facingslug = "strategy"
    else:
        raise ValidationError(f"getTopicByQID passed bad qid {qid} (Unknown prefix).")
    return facingslug

def getTopicByQID(qid):
    facingslug = None
    if qid.startswith("R"):
        facingslug = "researcher"
    elif qid.startswith("D"):
        facingslug = "data"
    elif qid.startswith("SW"):
        facingslug = "software"
    elif qid.startswith("SY"):
        facingslug = "systems"
    elif qid.startswith("SP"):
        facingslug = "strategy"
    else:
        raise ValidationError(f"getTopicByQID passed bad qid {qid} (Unknown prefix).")
    facing = Facing.objects.get(facingslug)
    topic = facing.capmodel_topics.get(getSlugForTopicQID(qid))
    return topic


def addNewTopic(qid, slug, facing, index, display_name, description=None):
    # Question: do we need to add this to the topic_QID_to_slug_mapping?
    # Yes, because the input fill will not have slugs
    t, created = CapabilitiesTopic.objects.get_or_create(
            slug=slug,
            facing=facing,
            index=index,
        )
    if not created:
        print(f"Warning: Attempt to create Topic with slug:{slug} and display name {display_name}; topic already exists!")
    else:
        t.contents.get_or_create(display_name=display_name, description=description)
        t.save()
        topic_QID_to_slug_mapping[qid] = slug
    return t

# Note that this can only be used to update topic details and order within a facing
# It CANNOT be used to move a topic to a new facing. That requires creating a new topic and adding
# new questions to it.
def update_capmodel_topic(qid, facing, new_index, new_display_name, new_description=None):
    try: 
        slug = getSlugForTopicQID(qid)
        t = CapabilitiesTopic.objects.get(slug=slug,facing=facing)
    except CapabilitiesTopic.DoesNotExist:
        raise ValidationError(f"No CapabilitiesTopic found with qid {qid} (slug {slug}) in facing {facing}.")

    # 
    # update the text, etc. for the new one. 
    t.index = new_index
    content = t.contents.get(language="en")
    content.display_name=new_display_name
    if new_description:
        content.description=new_description
    content.save()
    t.save()
    print(f"Updated Topic: {qid} Name: {new_display_name}")

    return t

# slug is a string, topic should be an object
def addNewCapabilityQuestion(qid, slug, topic, index, is_essential, text, help_text, short_text, update_time=None):
    # Pass in update_time so all the changes happen together and as of a particular date. Will default to timezone.now()
    at = update_time or timezone.now()
    # Note that this only checks for duplicate calls. This does not ensure that there is not a previous
    # question with the given QID and slug. Callers MUST handle that before calling this. 
    q, created = CapabilitiesQuestion.objects.get_or_create(
        slug=slug,
        topic=topic,
        index=index,
        is_essential=is_essential,
        valid_after=at,
    )
    if not created:
        print(f"Warning: Attempt to create Question with slug:{slug}, QID:{qid}, and Short name {short_text}; question already exists!")
    else:
        q.attrs["legacy_qid"] = qid
        # TODO handle multiple languages
        q.contents.get_or_create(text=text, help_text=help_text, shorttext=short_text)
        q.save()
    return q
    
# This does not delete the question, but does mark it as no longer valid so it disappears from new assessments
def removeCapabilityQuestion(qid, update_time=None):
    # Pass in update_time so all the changes happen together. Will default to timezone.now()
    at = update_time or timezone.now()
    try:
        question = CapabilitiesQuestion.objects.filter_valid(at=at).get(attrs__legacy_qid=qid)
        question.valid_before = at
        question.save()
    except CapabilitiesQuestion.DoesNotExist:
        raise ValidationError(f"No CapabilitiesQuestion found with QID {qid} that is valid at {at}.")
    except CapabilitiesQuestion.MultipleObjectsReturned:
        raise ValidationError(f"Multiple CapabilitiesQuestions found with QID {qid} that are valid at {at}.")


def update_capmodel_question(question, new_topic, new_index, is_essential, new_text, new_help_text, new_short_text, suffix, update_time=None):
    # Pass in update_time so all the changes happen together. Will default to timezone.now()
    # Each item has a topic indicator followed by the associated list of questions. The topic indicator is 
    at = update_time or timezone.now()
    # We have to clone the existing question to preserve the old one for previous versions, and then 
    # update the text, etc. for the new one. 
    # We cannot have two questions with the same slug and topic, so we append a suffix to the question slug
    newq = apps.get_model("nexus", "CapabilitiesQuestion").objects.copy(question, suffix, copy_contents=False, update_time=at)
    newq.contents.get_or_create(text=new_text, help_text=new_help_text, shorttext=new_short_text)
    newq.topic = new_topic
    newq.index = new_index
    newq.is_essential = is_essential
    # TODO need to make a new slug to keep DB happy. Is it enough to append a "_v3" to the slug? 
    # Review code to see. 
    newq.save()
    return

new_q_slugs = {
    "R1.6" : "ext_training", 
    "R2.7" : "inst_rsrcs_aware", 
    "R2.8" : "ext_rsrcs_aware", 
    "R3.3" : "emerging_tech_support", 
    "R5.1" : "user_supp_track", 
    "SW6.5" : "llm_apps", 
    "SY1.6" : "sys_docs", 
    "SY1.7" : "ident_role_mgmnt", 
    "SP7.5" : "cybersec_ass_supp", 
    "SP7.6" : "faculty_equip", 
}

"""
# add_or_update_questions_by_topic_in_facing Expects facing info like this:
data_facing = [
    [ "D8", "Data Management, Discovery, and Creation", # Topic QID and Display Name
        [   # List of questions in topic, in order
            ['D1.1',                                        # Question QID 
            'Do researchers ... {Data Creation Resources}', # Question text (HTML) and short-text in brackets
            "<p>For example...",                            # Question help text (HTML)
            'essential:True'                                # boolean: is_essential
            ], ...
        ], ...
    ], 
]
"""
# suffix will be appended to all updated question slugs to ensure uniqueness in the DB (mostly for serialization)
# Topic QID regex ^[A-Z]{1,2}\d{1,2}$
# Question QID regex ^[A-Z]{1,2}\d{1,2}\.\d{1,2}$
def add_or_update_questions_for_facing(facing_info, facing_slug, suffix, at_time):
    tindex = 0
    facing = Facing.objects.get(slug=facing_slug)
    print(f"add_or_update_questions_for_facing: {facing_slug}")
    for topic in facing_info:
        tqid = topic[0]
        if not topicQIDpattern.fullmatch(tqid):
            print(f"Bad or missing Topic QID: {tqid}")
            continue    # Skip this (emtpy?) structure
        tname = topic[1]
        # Update the topic. Note there is no update time

        tobj = update_capmodel_topic(tqid, facing, tindex, tname)
        tindex = tindex+1
        questions = topic[2]
        qindex = 0
        for question in questions:
            qqid = question[0]
            if not questionQIDpattern.fullmatch(qqid):
                print(f"Bad or missing Question QID: {qqid}")
                continue    # Skip this (emtpy?) structure
            pieces = question[1].split(" {",1)
            print(f"Question info: qid: {qqid} text and short: {pieces}")
            qtext = pieces[0]
            if len(pieces) == 1:
                qshort = "Missing short text!"
            else: 
                qshort = pieces[1].split("}", 1)[0] # There may be multiple shorts - ignore all but the first. 
            qhelp = question[2]
            is_essential = True if "True" in question[3] else False
            add_or_update_capmodel_question(qqid, tobj, qindex, is_essential, qtext, qhelp, qshort, suffix, update_time=at_time)
            qindex = qindex+1


def add_or_update_capmodel_question(qid, new_topic, new_index, is_essential, new_text, new_help_text, new_short_text, suffix, update_time=None):
    # Pass in update_time so all the changes happen together. Will default to timezone.now()
    # This will look for an existing question with the passed QID, and if found will update that one, 
    # and otherwise will create a new one. 
    at = update_time or timezone.now()
    try:
        question = CapabilitiesQuestion.objects.filter_valid(at=at).get(attrs__legacy_qid=qid)
        # question exists and must be updated. This is naive and only handles the default language. 
        # TODO Once we have translations, this will have to be extended to handle multiple languages. 
        print(f"Updating Question: {qid} Short: {new_short_text}")
        return update_capmodel_question(question, new_topic, new_index, is_essential, new_text, new_help_text, new_short_text, suffix, at)
    except CapabilitiesQuestion.MultipleObjectsReturned:
        raise ValidationError(f"Multiple CapabilitiesQuestions found with QID {qid} that are valid at {at}.")
    except CapabilitiesQuestion.DoesNotExist:
        # This just means we have to add a new one
        # We need to map the new slugs - hack!
        slug = new_q_slugs[qid]
        print(f"Adding Question: {qid} slug:{slug} Short: {new_short_text}")
        return addNewCapabilityQuestion(qid, slug, new_topic, new_index, is_essential, new_text, new_help_text, new_short_text, at)
    
def verify_deleted_topic(topic_qid, at_time):
    # Need to find all questions valid after update time contained in the topic. Should be empty. 
    topicslug = getSlugForTopicQID(topic_qid)
    facingslug = getFacingSlugForTopicQID(topic_qid)
    questions = CapabilitiesQuestion.objects.filter_valid(at=at_time).filter(topic__facing__slug=facingslug).filter(topic__slug=topicslug)
    if questions.exists:
        raise RuntimeError(f"Found questions still tied to Topic: {topic_qid} ({facingslug}.{topicslug}) at: {at_time}")

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
                assessment = CapabilitiesAssessment.objects.create(profile=profile, override_create_time=datetime(int(profile.year), 6, 1, tzinfo=timezone.utc))

                assessment.review_status = (
                    CapabilitiesAssessment.ReviewStatusChoices.APPROVED
                )
                assessment.review_time = datetime(int(profile.year), 1, 1, tzinfo=timezone.utc)
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

INTL_PREFIX = 'Intl:'       # Denotes non-US/Canada country names in "State" field
INTL_SKIP = len(INTL_PREFIX)
CANADA_PREFIX = 'Canada:'  # Denotes Canada province names in "State" field
CANADA_SKIP = len(CANADA_PREFIX)

def load_legacy_profiles_data(path):
    profiles_loaded = 0
    print("Loading legacy profiles...")
    user = get_user_model().objects.first()

    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if DEBUGMODE:
                print(row)
            structure = row["Structure"] if row["Structure"] != "" else None
            reporting = row["Reporting"] if row["Reporting"] != "" else None
            try:
                if row["UnitID"].isnumeric():
                    institution = Institution.objects.get(ipeds_unitid=row["UnitID"])
                else:
                    institution = Institution.objects.get(internet_domain=row["UnitID"])
            except Institution.DoesNotExist:
                if DEBUGMODE:
                    print("Could not find institution for {}".format(row))
                try:
                    input_state=row["State"]
                    if input_state.startswith(INTL_PREFIX):
                        country = input_state[INTL_SKIP:]
                        state = None
                        region = Institution.RegionChoices.INTERNATIONAL
                    elif input_state.startswith(CANADA_PREFIX):
                        country = 'Canada'
                        state = input_state[CANADA_SKIP:]
                        region = Institution.RegionChoices.CANADA
                    else:
                        country='USA'
                        state = input_state
                        region = None       # Not in the input - will need to adjust by hand
                    institution, _ = Institution.objects.get_or_create(
                        name=row["Name"], 
                        country=country,
                        ipeds_region=region,
                        state_or_province=state,
                        # ipeds_unitid=row["UnitID"], We are only here if there was not UnitID match
                        defaults={
                            "internet_domain": row["UnitID"],
                            "list_as_contributor": True,            # No assessment so no risk to default to True
                            # Since we do not know of them, assume these are all False 
                            # Most of them are non-US, so False is appropriate
                            "ipeds_hbcu":Institution.HBCUChoices.NOT_AN_HBCU,
                            "ipeds_pbi":Institution.PBIChoices.NOT_A_PBI,
                            "ipeds_tcu":Institution.TCUChoices.NOT_A_TCU,
                            "ipeds_hsi":Institution.HSIChoices.NOT_AN_HSI,
                            "ipeds_aanapisi_annh":Institution.AANAPISI_ANNHChoices.NOT_AN_AANAPISI_ANNH,
                            "ipeds_msi":Institution.MSIChoices.NOT_AN_MSI,
                            "ipeds_epscor":Institution.EPSCORChoices.NOT_EPSCOR,
                            "ipeds_land_grant":Institution.LandGrantChoices.NOT_A_LAND_GRANT_INSTITUTION,
                            },
                       )
                    #institution
                except IntegrityError as e:
                    print(e, row)
                    continue
                if DEBUGMODE:
                    print("Created new institution for {}".format(row))

            if profile := institution.profiles.filter(year=row["Year"]).first():
                # There is a chance someone created a 1.1 profile and then a 2.0 profile, both in 2023.
                if int(row["Year"]) == 2023:
                    print(f'Profile: {row["Name"]} ({row["Year"]}) already exists!  Skipping...')
                else:
                    if DEBUGMODE:
                        print(f'Found duplicate pre-2023 Profile: {row["Name"]} ({row["Year"]}). (load_legacy_profiles_data run twice? Ignoring...)')
                updated = False
                if profile.structure is None and not (structure is None):
                    profile.structure = structure
                    updated = True
                    if DEBUGMODE:
                        print(f'Updating existing Profile {row["Name"]} ({row["Year"]} with structure: {row["Structure"]}')
                if profile.org_chart is None and not (reporting is None):
                    profile.org_chart = reporting
                    updated = True
                    if DEBUGMODE:
                        print(f'Updating existing Profile {row["Name"]} ({row["Year"]} with org_chart: {row["Reporting"]}')
                if updated:
                    profile.save()

            else: 
                profile = institution.profiles.create(year=row["Year"], structure=structure, org_chart=reporting, created_by=user)
                if DEBUGMODE:
                    print(f'Created new Profile: {row["Name"]} ({row["Year"]})')
                profiles_loaded += 1

    print(f'Loaded {profiles_loaded} profiles.')

# deprecated("Use merge_institutions_into_primary() instead.")
def merge_institutions(institutions):
    return merge_institutions_into_primary(institutions[0], institutions[1:])

def merge_institutions_into_primary(primary, merge_list, no_merge=True, verbose=False):
    """
    Merge the institutions into the first one in the list, for deduplication.
    If no_merge is true (the default) this will only describe actions, and will not implement them. 
    WARNING: Make sure all FKs to the Institution model are included in this method before running it in prod. As of writing, there were 4.
    TODO Refine to check that no data will be lost in the merge, e.g. important names/descriptions on each additional Institution record. This is a destructive operation.
    """
    with transaction.atomic():
        for institution in merge_list:
            print(f"Merging: {institution}({institution.pk}) into primary: {primary}({primary.pk})")
            for profile in institution.profiles.all():
                if no_merge or verbose:
                    print(f"Moving profile: {profile} to primary institution.")
                if not no_merge:
                    profile.institution = primary
                    profile.save()
            for idp in institution.cilogon_idps.all():
                if no_merge or verbose:
                    print(f"Moving IDP: {idp} to primary institution.")
                if not no_merge:
                    idp.institution = primary
                    idp.save()
            for affiliation in institution.user_affiliations.all():
                if primary.user_affiliations.filter(user=affiliation.user).exists():
                    print(f"Primary institution already has User affiliation for: {affiliation.user}.")
                else:
                    if no_merge or verbose:
                        print(f"Moving User affiliation for: {affiliation.user} to primary institution.")
                    if not no_merge:
                        affiliation.institution = primary
                        affiliation.save()
            for request in institution.affiliation_requests.all():
                if no_merge or verbose:
                    print(f"Moving Affiliation Request for: {request.user} (with email {request.email}) to primary institution.")
                if not no_merge:
                    request.institution = primary
                    request.save()
            # Check all the fields to preserve data on the "dupes"
            if not primary.country and institution.country:
                if no_merge or verbose:
                    print(f"Copy merge institution country: {institution.country} to primary institution.")
                if not no_merge:
                    primary.country = institution.country
            if not primary.state_or_province and institution.state_or_province:
                if no_merge or verbose:
                    print(f"Copy merge institution state_or_province: {institution.state_or_province} to primary institution.")
                if not no_merge:
                    primary.state_or_province = institution.state_or_province
            if not primary.ipeds_unitid and institution.ipeds_unitid:
                # Note that ipeds_unitid must be unique among institutions, so we have to remove it from the old instiution first. 
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_unitid: {institution.ipeds_unitid} to primary institution.")
                if not no_merge:
                    ipeds_unitid = institution.ipeds_unitid
                    institution.ipeds_unitid = None
                    institution.save()
                    primary.ipeds_unitid = institution.ipeds_unitid
            if not primary.ipeds_sector and institution.ipeds_sector:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_sector: {institution.ipeds_sector} to primary institution.")
                if not no_merge:
                    primary.ipeds_sector = institution.ipeds_sector
            if not primary.ipeds_level and institution.ipeds_level:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_level: {institution.ipeds_level} to primary institution.")
                if not no_merge:
                    primary.ipeds_level = institution.ipeds_level
            if not primary.ipeds_control and institution.ipeds_control:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_control: {institution.ipeds_control} to primary institution.")
                if not no_merge:
                    primary.ipeds_control = institution.ipeds_control
            if not primary.ipeds_hbcu and institution.ipeds_hbcu:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_hbcu: {institution.ipeds_hbcu} to primary institution.")
                if not no_merge:
                    primary.ipeds_hbcu = institution.ipeds_hbcu
            if not primary.ipeds_pbi and institution.ipeds_pbi:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_pbi: {institution.ipeds_pbi} to primary institution.")
                if not no_merge:
                    primary.ipeds_pbi = institution.ipeds_pbi
            if not primary.ipeds_tcu and institution.ipeds_tcu:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_tcu: {institution.ipeds_tcu} to primary institution.")
                if not no_merge:
                    primary.ipeds_tcu = institution.ipeds_tcu
            if not primary.ipeds_hsi and institution.ipeds_hsi:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_hsi: {institution.ipeds_hsi} to primary institution.")
                if not no_merge:
                    primary.ipeds_hsi = institution.ipeds_hsi
            if not primary.ipeds_aanapisi_annh and institution.ipeds_aanapisi_annh:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_aanapisi_annh: {institution.ipeds_aanapisi_annh} to primary institution.")
                if not no_merge:
                    primary.ipeds_aanapisi_annh = institution.ipeds_aanapisi_annh
            if not primary.ipeds_msi and institution.ipeds_msi:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_msi: {institution.ipeds_msi} to primary institution.")
                if not no_merge:
                    primary.ipeds_msi = institution.ipeds_msi
            if not primary.ipeds_epscor and institution.ipeds_epscor:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_epscor: {institution.ipeds_epscor} to primary institution.")
                if not no_merge:
                    primary.ipeds_epscor = institution.ipeds_epscor
            if not primary.ipeds_land_grant and institution.ipeds_land_grant:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_land_grant: {institution.ipeds_land_grant} to primary institution.")
                if not no_merge:
                    primary.ipeds_land_grant = institution.ipeds_land_grant
            if not primary.ipeds_urbanization and institution.ipeds_urbanization:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_urbanization: {institution.ipeds_urbanization} to primary institution.")
                if not no_merge:
                    primary.ipeds_urbanization = institution.ipeds_urbanization
            if not primary.ipeds_size and institution.ipeds_size:
                if no_merge or verbose:
                    print(f"Copy merge institution ipeds_size: {institution.ipeds_size} to primary institution.")
                if not no_merge:
                    primary.ipeds_size = institution.ipeds_size
            if not primary.carnegie_classification and institution.carnegie_classification:
                if no_merge or verbose:
                    print(f"Copy merge institution carnegie_classification: {institution.carnegie_classification} to primary institution.")
                if not no_merge:
                    primary.carnegie_classification = institution.carnegie_classification
            if not primary.undergrad_pop and institution.undergrad_pop:
                if no_merge or verbose:
                    print(f"Copy merge institution undergrad_pop: {institution.undergrad_pop} to primary institution.")
                if not no_merge:
                    primary.undergrad_pop = institution.undergrad_pop
            if not primary.grad_pop and institution.grad_pop:
                if no_merge or verbose:
                    print(f"Copy merge institution grad_pop: {institution.grad_pop} to primary institution.")
                if not no_merge:
                    primary.grad_pop = institution.grad_pop
            if not primary.student_pop and institution.student_pop:
                if no_merge or verbose:
                    print(f"Copy merge institution student_pop: {institution.student_pop} to primary institution.")
                if not no_merge:
                    primary.student_pop = institution.student_pop
            if not primary.research_expenditure and institution.research_expenditure:
                if no_merge or verbose:
                    print(f"Copy merge institution research_expenditure: {institution.research_expenditure} to primary institution.")
                if not no_merge:
                    primary.research_expenditure = institution.research_expenditure

            if not no_merge:
                primary.save()
                institution.delete()
    return primary

# Includes a name check just for safety. First pk in list
def merge_institutions_by_pks(primary_pk, merge_pks, name_check, no_merge=True, verbose=False ):
    institutions_to_merge = []
    print(f"merge_institutions_by_pks primary: {primary_pk}, to merge: {merge_pks} with name: {name_check}"+"(Test only, no merge)" if no_merge else "")
    try:
        primary = Institution.objects.get(pk=primary_pk, name__icontains=name_check)
    except Institution.DoesNotExist:
        raise ValidationError(f"No institution found with for primary pk:[{primary_pk}] and name matching ({name_check}).")
    
    for pk in merge_pks:
        try:
            inst = Institution.objects.get(pk=pk, name__icontains=name_check)
        except Institution.DoesNotExist:
            raise ValidationError(f"No institution found with for merge pk:[{pk}] and name matching ({name_check}).")
        institutions_to_merge.append(inst)
        
    merge_institutions_into_primary(primary, institutions_to_merge, no_merge=no_merge, verbose=verbose)
    print(f"Merged institutions into base: {primary.name} ({primary.pk})")
