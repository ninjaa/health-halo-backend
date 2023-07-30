from flask import Flask, stream_with_context, request, Response, make_response
from dotenv import load_dotenv
import psycopg2
import os
from tabulate import tabulate
import functools
import time
import re
from anthropic2.dict_to_pretty_xml import dict_to_pretty_xml
from twilio.rest import Client

from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
anthropic = Anthropic(
    api_key=***REMOVED***)

# from dict_to_pretty_xml import dict_to_pretty_xml


load_dotenv()


def run_sql(query):
    # Connect to your database
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")

    connection = None
    try:
        connection = psycopg2.connect(
            database=database, user=user, password=password, host=host, port=port)
        cursor = connection.cursor()

        # Execute the SQL query
        cursor.execute(query)

        # Fetch column names
        column_names = [desc[0] for desc in cursor.description]

        # Fetch all rows
        rows = cursor.fetchall()

        print(column_names)
        print(rows)

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Use tabulate to generate markdown table
        return tabulate(rows, headers=column_names, tablefmt='pipe')

    except Exception as e:
        raise e

    finally:
        if connection:
            connection.close()


functions = []


def doc_extractor(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    doc_lines = func.__doc__.strip().split("\n")
    description = doc_lines[0]

    # Extract details if present
    details_index = None
    for idx, line in enumerate(doc_lines):
        if line.strip() == "Details:":
            details_index = idx
            break

    if details_index is not None:
        description += " " + " ".join([line.strip()
                                      for line in doc_lines[details_index+1:]])

    raises = None
    for line in doc_lines:
        if "Raises:" in line:
            raises = line.split("Raises:")[1].strip()
            break

    arg_list = list(func.__annotations__.keys())
    if 'return' in arg_list:
        arg_list.remove('return')

    args_str = []
    for arg in arg_list:
        arg_description_match = re.search(
            rf"{arg} \({func.__annotations__[arg]}\): (.+)", func.__doc__)
        arg_description = arg_description_match.group(
            1) if arg_description_match else "Description needed."
        args_str.append(
            f"{arg} ({func.__annotations__[arg]}): {arg_description}")

    # Extract return information
    return_info = None
    return_start = None
    for idx, line in enumerate(doc_lines):
        if "Returns:" in line:
            return_start = idx
            break

    if return_start is not None:
        return_lines = []
        for line in doc_lines[return_start+1:]:
            if not line.strip():
                break
            return_lines.append(line.strip())
        return_info = ' '.join(return_lines)

    function_dict = {
        "name": func.__name__,
        "description": description,
        "required_arguments": args_str,
        "returns": f"{func.__annotations__['return']}: {return_info}" if 'return' in func.__annotations__ and return_info else None,
        "raises": raises,
        "example_call": f"{func.__name__}({', '.join([f'{arg}=value' for arg in arg_list])})"
    }

    functions.append(function_dict)

    return wrapper


# @doc_extractor
# def example_function(param1: "Type1", param2: "Type2") -> "ReturnType":
#     """
#     This is an example function description.

#     Raises:
#     Exception: In case something happens.

#     Returns:
#     ReturnType: Description of return value.
#     """
#     pass


@doc_extractor
def get_notes(start_index: "int", end_index: "int") -> "table":
    """
    Fetches medical record notes for the current patient from `start_index` to `end_index`.

    Arguments:
    start_index (int): The starting index for the notes retrieval.
    end_index (int): The ending index for the notes retrieval.

    Raises:
    ValueError: if the db has gone away.

    Returns:
    table: A table of medical record notes. ALWAYS remember to cite information from notes eg [Progress Note](http://localhost:8000/notes/4). NEVER include links that aren't to note sources.
    """
    return run_sql("SELECT * FROM notes_data LIMIT 5")


@doc_extractor
def get_notes_by_type(type: "str") -> "table":
    """
    Fetches medical record notes for the current patient filtered by the note type provided.

    Arguments:
    type (str): The type of note to be retrieved.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Here is the underlying table schema:
    - Table: notes_data
    - Columns: id, date, note_type, note_content, source_url
    - Distinct note types (can change on an ad-hoc basis): "Social Work Screen Comments", "Review of Systems Documentation", "Social Work Clinical Assessment", "PT Precaution", "ICU Weekly Summary Nursing", "ICU Progress (Systems) Nursing", "Central Vascular Catheter Procedure", "Procedure Note", "Genetics Consultation", "Subjective Statement PT", "NICU Admission MD", "General Surgery ICU Progress MD", "Case Management Planning", "Lactation Support Consultation", "Final", "RN Shift Events", "Occupational Therapy Inpatient", "Education Topic Details", "Lab Order/Specimen Not Received Notify", "Report", "cm reason for admission screening tool", "Chief Complaint PT", "Echocardiogram Note", "Assessment and Plan - No Dx", "History of Present Illness Documentation", "Powerplan Not Completed Notification", "PT Treatment Recommendations", "Gram", "Surgery - Patient Summary", "Reason for Referral PT", "Development Comments", "Chaplaincy Inpatient", "Nutrition Consultation", "ICU Admission Nursing", "Inpatient Nursing", "Endocrinology Consultation", "Case Management Note", "Social Work Inpatient Confidential", "General Surgery Admission MD", "Nursing Admission Assessment.", "Hospital Course", "NICU Progress MD", "Physical Examination Documentation", "General Surgery Inpatient MD", "Preliminary Report", "NICU Note Overall Impression"

    Returns:
    table: A table of medical record notes. ALWAYS remember to cite information from notes eg [Progress Note](http://localhost:8000/notes/4). NEVER include links that aren't to note sources.
    """
    return run_sql("SELECT * FROM notes_data WHERE note_type ILIKE '%{type}%'")


@doc_extractor
def search_notes(search_str: "str") -> "table":
    """
    Searches medical record notes for the current patient filtered by the note type provided.

    Arguments:
    search_str (str): search string to search by.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Here is the underlying table schema:
    - Table: notes_data
    - Columns: id, date, note_type, note_content, source_url
    - Distinct note types (can change on an ad-hoc basis): "Social Work Screen Comments", "Review of Systems Documentation", "Social Work Clinical Assessment", "PT Precaution", "ICU Weekly Summary Nursing", "ICU Progress (Systems) Nursing", "Central Vascular Catheter Procedure", "Procedure Note", "Genetics Consultation", "Subjective Statement PT", "NICU Admission MD", "General Surgery ICU Progress MD", "Case Management Planning", "Lactation Support Consultation", "Final", "RN Shift Events", "Occupational Therapy Inpatient", "Education Topic Details", "Lab Order/Specimen Not Received Notify", "Report", "cm reason for admission screening tool", "Chief Complaint PT", "Echocardiogram Note", "Assessment and Plan - No Dx", "History of Present Illness Documentation", "Powerplan Not Completed Notification", "PT Treatment Recommendations", "Gram", "Surgery - Patient Summary", "Reason for Referral PT", "Development Comments", "Chaplaincy Inpatient", "Nutrition Consultation", "ICU Admission Nursing", "Inpatient Nursing", "Endocrinology Consultation", "Case Management Note", "Social Work Inpatient Confidential", "General Surgery Admission MD", "Nursing Admission Assessment.", "Hospital Course", "NICU Progress MD", "Physical Examination Documentation", "General Surgery Inpatient MD", "Preliminary Report", "NICU Note Overall Impression"
    - call this function repeatedly with related keywords like baby, infant and so on to get more notes if you don't get what you're looking for on the first pass

    Returns:
    table: A table of medical record notes. remember to always cite the source URL if you use information from the notes.
    """

    return run_sql(f"SELECT * FROM notes_data WHERE note_type ILIKE '%{search_str}%' OR note_content ILIKE '%{search_str}%' LIMIT 5")


@doc_extractor
def get_labs(start_index: "int" = 0, end_index: "int" = 10) -> "table":
    """
    Fetches lab data for the current patient from `start_index` to `end_index`.

    Arguments:
    start_index (int): The starting index for the lab data retrieval.
    end_index (int): The ending index for the lab data retrieval.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Table: lab_data
    - Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high
    - Distinct lab values (can change on an ad-hoc basis: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"

    Returns:
    table: A table of medical record lab results. ALWAYS remember to cite information from notes eg [Progress Note](http://localhost:8000/notes/4). NEVER include links that aren't to note sources.
    """
    return run_sql("SELECT * FROM lab_data LIMIT 10")


@doc_extractor
def get_labs_by_type(type: "str") -> "table":
    """
    Fetches lab data for the current patient filtered by the lab type provided.

    Arguments:
    type (str): The type of lab to be retrieved.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Table: lab_data
    - Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high
    - Distinct lab values (can change on an ad-hoc basis: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"

    Returns:
    table: A table of medical record lab results.
    """
    return run_sql(f"SELECT * FROM lab_data WHERE lab ILIKE '%{type}%'")


@doc_extractor
def get_count_notes() -> "int":
    """
    Returns the total count of medical record notes for the current patient.

    Raises:
    ValueError: if the db has gone away.

    Returns:
    int: The total count of medical record notes.
    """
    return run_sql("SELECT COUNT(*) from notes_data")


@doc_extractor
def get_count_labs() -> "int":
    """
    Returns the total count of lab records for the current patient.

    Raises:
    ValueError: if the db has gone away.

    Returns:
    int: The total count of lab records.
    """
    return run_sql("SELECT COUNT(*) from lab_data")


@doc_extractor
def search_labs(search_str: "str") -> "table":
    """
    Seraches lab data for the current patient from `start_index` to `end_index`.

    Arguments:
    search_str (int): search string.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Table: lab_data
    - Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high
    - Distinct lab values (can change on an ad-hoc basis: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"

    Returns:
    table: A table of medical record lab results.
    """
    return run_sql(f"SELECT * FROM lab_data WHERE lab ILIKE '%{search_str}%' OR source ILIKE '%{search_str}%' LIMIT 10")


@doc_extractor
def get_meds(start_index: "int" = 0, end_index: "int" = 10) -> "table":
    """
    Fetches medications listings for the current patient from `start_index` to `end_index`.

    Arguments:
    start_index (int): The starting index for the med data retrieval.
    end_index (int): The ending index for the med data retrieval.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Table: med_data
    - Columns: id, name, type, dose , start, end, unit
    - Distinct med values (can change on an ad-hoc basis: "cefepime", "DOPamine", "FEN", "vancomycin", "furosemide", "D17.5W 500 mL[5074049391]", "D5W 1,000 mL + sodium ACETATE, IVF 77 mEq[5065323385]", "D10W 1,000 mL + sodium ACETATE, IVF 20 mEq[5063225641]", "silver sulfADIAZINE topical", "fentaNYL", "DERM", "D5W 1,000 mL + sodium ACETATE, IVF 154 mEq[5064867545]", "glycerin", "dexAMETHasone", "Parenteral Nutrition 74.4 mL[5062322395]", "MISC", "acetaminophen", "ENDO", "dexmedeTOMIDine", "caffeine", "fat emulsion 20%, intravenous 26.4 mL[5062322399]")
    Returns:
    table: A table of med record results.
    """
    return run_sql("SELECT * FROM med_data LIMIT 10")


@doc_extractor
def get_meds_by_type(type: "str") -> "table":
    """
    Fetches medications data for the current patient filtered by the medication type provided.

    Arguments:
    type (str): The type of med to be retrieved.

    Raises:
    ValueError: if the db has gone away.

    Details:
    - Table: med_data
    - Columns: id, name, type, dose , start, end, unit
    - Distinct med type values (can change on an ad-hoc basis: "cefepime", "DOPamine", "FEN", "vancomycin", "furosemide", "D17.5W 500 mL[5074049391]", "D5W 1,000 mL + sodium ACETATE, IVF 77 mEq[5065323385]", "D10W 1,000 mL + sodium ACETATE, IVF 20 mEq[5063225641]", "silver sulfADIAZINE topical", "fentaNYL", "DERM", "D5W 1,000 mL + sodium ACETATE, IVF 154 mEq[5064867545]", "glycerin", "dexAMETHasone", "Parenteral Nutrition 74.4 mL[5062322395]", "MISC", "acetaminophen", "ENDO", "dexmedeTOMIDine", "caffeine", "fat emulsion 20%, intravenous 26.4 mL[5062322399]")
    Returns:
    table: A table of med record results.
    """
    return run_sql(f"SELECT * FROM med_data WHERE type ILIKE '%{type}%' LIMIT 10")


@doc_extractor
def get_count_meds() -> "int":
    """
    Returns the total count of medication records for the current patient.
    Raises:

    ValueError: if the db has gone away.

    Returns:
    int: The total count of med records.
    """
    return run_sql("SELECT COUNT(*) from med_data")


@doc_extractor
def notify_team_by_sms(message: "str") -> "str":
    """
    Sends a message to the team via SMS. Please note the message should be less than 300 characters

    Arguments:
    message (str): The message to send (less than 300 characters!).

    Raises:
    ValueError: if the SMS service has gone away or failed.

    Returns:
    str: A confirmation message.
    """
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)

    message = client.messages \
        .create(
            body=message,
            from_=os.environ['TWILIO_PHONE_NUMBER'],
            to=os.environ['TWILIO_TEAM_PHONE_NUMBER']
        )

    return f"Message sent: {message}"


XML_FUNCTION_DEFINITIONS = dict_to_pretty_xml(functions)

print(XML_FUNCTION_DEFINITIONS)


def get_initial_prompt(question):
    TODAYS_DATE_STRING = "2023-06-08 12:35:02"

    INITIAL_PROMPT = f"""{HUMAN_PROMPT} 
    You are the world's most advanced medical research assistant AI that has been equipped with the following function(s) to help you answer a <question>. 
    Your goal is to answer the user's question to the best of your ability, using the function(s) to gather more information if necessary 
    to better answer the question. The result of a function call will be added to the conversation history as an observation. if you are unsure of where to find information, check patient notes. ALWAYS cite the source URL if you use information from the notes!

    Here are the only function(s) I have provided you with:

    Today's date is {TODAYS_DATE_STRING}.

{XML_FUNCTION_DEFINITIONS}

Here is an example of how you would correctly answer a question using a <function_call> and the corresponding <function_result>. Notice that you are free to think before deciding to make a <function_call> in the <scratchpad>:
​
<example>
<functions>
<function>
<function_name>get_current_temp</function_name>
<function_description>Gets the current temperature for a given city.</function_description>
<required_argument>city (str): The name of the city to get the temperature for.</required_argument>
<returns>int: The current temperature in degrees Fahrenheit.</returns>
<raises>ValueError: If city is not a valid city name.</raises>
<example_call>get_current_temp(city=\"New York\")</example_call>
</function>
</functions>
​
<question>What is the current temperature in San Francisco?</question>
​
<scratchpad>I do not have access to the current temperature in San Francisco so I should use a function to gather more information to answer this question. I have been equipped with the function get_current_temp that gets the current temperature for a given city so I should use that to gather more information.
​
I have double checked and made sure that I have been provided the get_current_temp function.
</scratchpad>
​
<function_call>get_current_temp(city=\"San Francisco\")</function_call>
​
<function_result>71</function_result>
​
<answer>The current temperature in San Francisco is 71 degrees Fahrenheit.</answer>
</example>
​

Note that the function arguments have been listed in the order that they should be passed into the function.

Do not modify or extend the provided functions under any circumstances. For example, calling get_current_temp() with additional parameters would be considered modifying the function which is not allowed. Please use the functions only as defined.

DO NOT use any functions that I have not equipped you with.

To call a function, output <function_call>insert specific function</function_call>. You will receive a <function_result> in response to your call that contains information that you can use to better answer the question.

Here is an example of how you would correctly answer a question using a <function_call> and the corresponding <function_result>. Notice that you are free to think before deciding to make a <function_call> in the <scratchpad>:

Remember, your goal is to answer the user's question to the best of your ability, using only the function(s) provided to gather more information if necessary to better answer the question.

Do not modify or extend the provided functions under any circumstances. For example, calling get_current_temp() with additional parameters would be modifying the function which is not allowed. Please use the functions only as defined.

The result of a function call will be added to the conversation history as an observation. Never make up the function result, just open the tag and let the Human insert the resul. If necessary, you can make multiple function calls and use all the functions I have equipped you with. Let's create a plan and then execute the plan. Double check your plan to make sure you don't call any functions that I haven't provided. Always return your final answer within  <answer></answer> tags and use markdown format. IMPORTANT: if you reference information from the patient notes, always include the source of each note in the answer in markdown format. eg [Progress Note](http://localhost:8000/notes/4). never include links that aren't to note sources. you should keep the source URL in the scratchpad so you can include it in your final answer.

The question to answer is <question>{question}</question>
    
    
    {AI_PROMPT}<scratchpad> I understand I cannot use functions that have not been provided to me to answer this question. I will ALWAYS remember to cite information from notes eg [Progress Note](http://localhost:8000/notes/4). I will never include links that aren't to note sources.
    """
    return INITIAL_PROMPT

def function_action(function_name):
    if function_name == "get_notes":
        return "Fetching medical record notes..."
    elif function_name == "get_notes_by_type":
        return "Fetching medical record notes filtered by note type..."
    elif function_name == "search_notes":
        return "Searching the medical record notes..."
    elif function_name == "get_labs":
        return "Fetching lab data..."
    elif function_name == "get_labs_by_type":
        return "Fetching lab data filtered by lab type..."
    elif function_name == "get_count_notes":
        return "Fetching the total count of medical record notes..."
    elif function_name == "get_count_labs":
        return "Fetching the total count of lab records..."
    elif function_name == "search_labs":
        return "Searching the lab data..."
    elif function_name == "get_meds":
        return "Fetching medications..."
    elif function_name == "get_meds_by_type":
        return "Fetching medication data filtered by medication type..."
    elif function_name == "get_count_meds":
        return "Fetching the total count of medication records..."
    elif function_name == "notify_team_by_sms":
        return "Sending a message to the team via SMS..."
    else:
        return "Executing..."
app = Flask(__name__)
@app.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    # Connect to your database
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")

    connection = None
    try:
        connection = psycopg2.connect(
            database=database, user=user, password=password, host=host, port=port)
        cursor = connection.cursor()

        # Execute the SQL query
        query = f"SELECT note_content FROM notes_data WHERE id = {note_id};"
        cursor.execute(query)

        # Fetch all rows
        rows = cursor.fetchall()

        # Close the cursor and connection
        cursor.close()
        connection.close()
        if rows:
                note_content = rows[0][0]
                resp = make_response(f'<html><body><h1 style="font-size: 2em;">{note_content}</h1></body></html>')
                resp.headers["Content-type"] = "text/html"
                return resp
        # return only the content of the note, which is assumed to be in the first column of the first row
        return rows[0][0] if rows else Response("Note not found", status=404)
    except Exception as e:
        return str(e)


@app.route('/conduct_chat', methods=['POST'])
def conduct_chat_endpoint():
    initial_messages = request.json.get('initial_messages')
    last_message = initial_messages[-1]
    question = last_message['content'] + " - remember to include the sources to notes if you reference any information from them!"

    def conduct_chat():
        current_prompt = get_initial_prompt(question)
        print(current_prompt)
        while True:
            yield '**🧠 Thinking**\n\n'
            answering = False
            stream = anthropic.completions.create(
                model="claude-2",
                max_tokens_to_sample=1000,
                prompt=current_prompt,
                stream=True,
            )
            buffer = ""
            for completion in stream:
                chunk = completion.completion
                print(chunk)
                buffer += chunk

                if answering:
                    if "</" in chunk:
                        # remove closing answer tag from chunk
                        chunk = chunk[:chunk.find("</")]
                        chunk = chunk + "\n"
                        yield chunk
                        return
                    yield chunk
                if "<answer>" in buffer:
                    # remove everything before the opening answer tag in buffer
                    buffer = buffer[buffer.find("<answer>")+len("<answer>"):]
                    answering = True
                    yield buffer
                if "</function_call>" in buffer and not answering:
                    # Extract the function call
                    # print(buffer)
                    function_call_match = re.search(
                        r"<function_call>\s*(.*?)\s*</function_call>", buffer, re.DOTALL)
                    function_call_content = function_call_match.group(
                        1) if function_call_match else None
                    print(function_call_content)
                    function_name = function_call_content.split("(")[0]
                    yield f'**⚙️ {function_action(function_name)}**\n\n'

                    result = eval(function_call_content)
                    current_prompt = current_prompt + buffer + \
                        "<function_result>" + result + "</function_result>"
                    break
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    return Response(conduct_chat(), headers=headers)


if __name__ == '__main__':
    app.run(port=8000)
