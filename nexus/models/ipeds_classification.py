from django.db import models


class IPEDSMixin(models.Model):
    """
    Includes fields defined by the Integrated Postsecondary Education Data System (IPEDS).

    Includes our Institutional classification which is based upon Carnegie classification, but with additions.

    https://nces.ed.gov/ipeds/
    """

    class Meta:
        abstract = True

    ipeds_unitid = models.BigIntegerField(
        "IPEDS Unit ID",
        unique=True,
        null=True,
        blank=True,
        help_text="IPEDS UnitID primarily for joining new data."
    )

    class SectorChoices(models.IntegerChoices):
        PUBLIC_4_YR = 1, "Public 4-yr"
        PRIVATE_4_YR = 2, "Private 4-yr"
        FOR_PROFIT_4_YR = 3, "For Profit 4-yr"
        PUBLIC_2_YR = 4, "Public 2-yr"
        PRIVATE_2_YR = 5, "Private 2-yr"
        FOR_PROFIT_2_YR = 6, "For Profit 2-yr"

    ipeds_sector = models.IntegerField(
        "Sector",
        choices=SectorChoices.choices,
        null=True,
        blank=True,
    )

    class LevelChoices(models.IntegerChoices):
        FOUR_OR_MORE = 1, "4 or more"
        TWO_TO_FOUR = 2, "2 to 4"

    ipeds_level = models.IntegerField(
        "Level",
        choices=LevelChoices.choices,
        null=True,
        blank=True,
    )

    class ControlChoices(models.IntegerChoices):
        PUBLIC = 1, "Public"
        PRIVATE_NON_PROFIT = 2, "Private non-profit"
        PRIVATE_FOR_PROFIT = 3, "Private for-profit"

    ipeds_control = models.IntegerField(
        "Public/Private",
        choices=ControlChoices.choices,
        null=True,
        blank=True,
    )

    class HBCUChoices(models.IntegerChoices):
        HBCU = 1, "HBCU"
        NOT_AN_HBCU = 2, "Not an HBCU"

    ipeds_hbcu = models.IntegerField(
        "Historically Black College or University",
        choices=HBCUChoices.choices,
        null=True,
        blank=True,
    )

    class PBIChoices(models.IntegerChoices):
        PBI = 1, "PBI"
        NOT_A_PBI = 2, "Not a PBI"

    ipeds_pbi = models.IntegerField(
        "Predominantly Black Institution",
        choices=PBIChoices.choices,
        null=True,
        blank=True,
    )

    class TCUChoices(models.IntegerChoices):
        TCU = 1, "TCU"
        NOT_A_TCU = 2, "Not a TCU"

    ipeds_tcu = models.IntegerField(
        "Tribal College or University",
        choices=TCUChoices.choices,
        null=True,
        blank=True,
    )

    class HSIChoices(models.IntegerChoices):
        HSI = 1, "HSI"
        NOT_AN_HSI = 2, "Not an HSI"

    ipeds_hsi = models.IntegerField(
        "Hispanic-Serving Institution",
        choices=HSIChoices.choices,
        null=True,
        blank=True,
    )

    class AANAPISI_ANNHChoices(models.IntegerChoices):
        AANAPISI_ANNH = 1, "AANAPISI or ANNH"
        NOT_AN_AANAPISI_ANNH = 2, "Not an AANAPISI or ANNH"

    ipeds_aanapisi_annh = models.IntegerField(
        "Asian American and Native American Pacific Islander Serving Institution and/or Alaska Native and Native Hawaiian Serving Institution",
        choices=AANAPISI_ANNHChoices.choices,
        null=True,
        blank=True,
    )

    class MSIChoices(models.IntegerChoices):
        MSI = 1, "An MSI"
        NOT_AN_MSI = 2, "Not an MSI"

    ipeds_msi = models.IntegerField(
        "Minority-Serving Institution",
        choices=MSIChoices.choices,
        null=True,
        blank=True,
    )

    class EPSCORChoices(models.IntegerChoices):
        EPSCOR = 1, "EPSCoR"
        NOT_EPSCOR = 2, "Not EPSCoR"

    ipeds_epscor = models.IntegerField(
        "EPSCoR Institution",
        choices=EPSCORChoices.choices,
        null=True,
        blank=True,
    )

    class UrbanizationChoices(models.IntegerChoices):
        CITY_LARGE = 11, "City: Large"
        CITY_MIDSIZE = 12, "City: Midsize"
        CITY_SMALL = 13, "City: Small"
        SUBURB_LARGE = 21, "Suburb: Large"
        SUBURB_MIDSIZE = 22, "Suburb: Midsize"
        SUBURB_SMALL = 23, "Suburb: Small"
        TOWN_FRINGE = 31, "Town: Fringe"
        TOWN_DISTANT = 32, "Town: Distant"
        TOWN_REMOTE = 33, "Town: Remote"
        RURAL_FRINGE = 41, "Rural: Fringe"
        RURAL_DISTANT = 42, "Rural: Distant"
        RURAL_REMOTE = 43, "Rural: Remote"
        NOT_AVAILABLE = -3, "{Not available}"

    ipeds_urbanization = models.IntegerField(
        "Urbanization",
        choices=UrbanizationChoices.choices,
        null=True,
        blank=True,
    )

    class LandGrantChoices(models.IntegerChoices):
        LAND_GRANT_INSTITUTION = 1, "Land Grant Institution"
        NOT_A_LAND_GRANT_INSTITUTION = 2, "Not a Land Grant Institution"

    ipeds_land_grant = models.IntegerField(
        "Land Grant Institution",
        choices=LandGrantChoices.choices,
        null=True,
        blank=True,
    )

    class CarnegieClassificationChoices(models.IntegerChoices):
        OTHER = 0, "Other RCD (Nat'l Labs/Facilities, etc.)"
        MIXED_BACC_ASSOC_ASSOC_DOM = 14, "Mixed Bacc/Assoc (Assoc. Dom.)"
        R1 = 15, "R1"
        R2 = 16, "R2"
        R3 = 17, "R3"
        M1 = 18, "M1"
        M2 = 19, "M2"
        M3 = 20, "M3"
        BACC_ARTS_AND_SCI = 21, "Bacc: Arts and Sci"
        BACC_DIVERSE = 22, "Bacc: Diverse"
        MIXED_BACC_ASSOC = 23, "Mixed Bacc/Assoc"
        FOUR_YR_FAITH_RELATED_INSTITUTIONS = 24, "4yr: Faith-Related Institutions"
        FOUR_YR_MED_SCHOOLS_CENTERS = 25, "4yr: Med Schools & Centers"
        FOUR_YR_OTHER_HEALTH_PROF_SCHOOLS = 26, "4yr: Other Health Prof. Schools"
        FOUR_YR_RESEARCH_INSTITUTIONS = 27, "4yr: Research Institutions"
        FOUR_YR_ENGINEERING_TECHNOLOGY_SCHOOLS = 28, "4yr: Engineering & Technology Schools",
        FOUR_YR_BUSINESS_MANAGEMENT_SCHOOLS = 29, "4yr: Business & Management Schools"
        FOUR_YR_ARTS_MUSIC_DESIGN_SCHOOLS = 30, "4yr: Arts, Music & Design Schools"
        FOUR_YR_LAW_SCHOOLS = 31, "4yr: Law Schools"
        FOUR_YR_OTHER_SPECIAL_FOCUS_INSTITUTIONS = 32, "4yr: Other Special Focus Institutions"
        TRIBAL_COLLEGES = 33, "Tribal Colleges"
        MISC = 1000, "Miscellaneous (Funders, Agencies, etc.)"
        INDUSTRY = 1001, "Industry Labs/Institutes"


    carnegie_classification = models.IntegerField(
        "Institutional Classification",
        choices=CarnegieClassificationChoices.choices,
        null=True,
        blank=True,
    )

    carnegie_longnames = [
        "R1: Doctoral Universities - Very high research activity", 
        "R2: Doctoral Universities - High research activity",
        "D/PU (R3): Doctoral/Professional Universities",
        "M1: Master's Colleges and Universities - Larger programs",
        "M2: Master's Colleges and Universities - Medium programs",
        "M3: Master's Colleges and Universities - Small programs",
    ]

    def carnegie_longname(self) :
        if self.carnegie_classification is None\
            or self.carnegie_classification < self.CarnegieClassificationChoices.MIXED_BACC_ASSOC_ASSOC_DOM \
            or self.carnegie_classification > self.CarnegieClassificationChoices.TRIBAL_COLLEGES :
            return "Other"
        if self.carnegie_classification == self.CarnegieClassificationChoices.MIXED_BACC_ASSOC_ASSOC_DOM \
            or self.carnegie_classification >= self.CarnegieClassificationChoices.BACC_ARTS_AND_SCI :
            return self.get_carnegie_classification_display()
        # self.carnegie_classification is between 15 and 20 inclusive (one of 6 values)
        return self.carnegie_longnames[self.carnegie_classification - self.CarnegieClassificationChoices.R1]

    class SizeChoices(models.IntegerChoices):
        UNDER_1000 = 1, "Under 1,000"
        BTW_1000_4999 = 2, "1,000 - 4,999"
        BTW_5000_9999 = 3, "5,000 - 9,999"
        BTW_10000_19999 = 4, "10,000 - 19,999"
        ABOVE_20000 = 5, "20,000 and above"
        # NOT_APPLICABLE = -2, "Not applicable"  # We disable this so that we can represent these as NULLs instead for better queryability

    ipeds_size = models.IntegerField(
        "Size Range (# of students)",
        choices=SizeChoices.choices,
        null=True,
        blank=True,
    )

    class RegionChoices(models.IntegerChoices):
        SERVICE_SCHOOLS = 0, "Service schools"
        NEW_ENGLAND = 1, "New England"
        MID_EAST = 2, "Mid East"
        GREAT_LAKES = 3, "Great Lakes"
        PLAINS = 4, "Plains"
        SOUTHEAST = 5, "Southeast"
        SOUTHWEST = 6, "Southwest"
        ROCKY_MOUNTAINS = 7, "Rocky Mountains"
        FAR_WEST = 8, "Far West"
        OTHER_U_S_JURISDICTIONS = 9, "Other U.S. jurisdictions"
        CANADA = 100, "Canada"
        INTERNATIONAL = 200, "International"

    ipeds_region = models.IntegerField(
        "Region",
        choices=RegionChoices.choices,
        null=True,
        blank=True,
    )
