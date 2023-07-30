from flask import Flask, stream_with_context, request, Response
import time
import re

from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
anthropic = Anthropic(api_key=***REMOVED***)

import functools
from tabulate import tabulate
from pprint import pprint
import os
import psycopg2
from dotenv import load_dotenv
# from dict_to_pretty_xml import dict_to_pretty_xml
import re


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
    table: A table of medical record notes.
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
    table: A table of medical record notes.
    """
    return run_sql("SELECT * FROM notes_data WHERE NOTE_TYPE = '{type}' LIMIT 5")


@doc_extractor
def get_labs(start_index: "int", end_index: "int") -> "table":
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
    table: A table of medical record lab results.
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
    return run_sql(f"SELECT * FROM lab_data WHERE lab_type={type}")


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
def get_initial_prompt(question):
    TODAYS_DATE_STRING = "2023-06-08 12:35:02"

    INITIAL_PROMPT = f"""{HUMAN_PROMPT} 
    You are a medical research assistant AI that has been equipped with the following function(s) to help you answer a <question>. 
    Your goal is to answer the user's question to the best of your ability, using the function(s) to gather more information if necessary 
    to better answer the question. The result of a function call will be added to the conversation history as an observation.

    Here are the only function(s) I have provided you with:

    Today's date is {TODAYS_DATE_STRING}.

<functions>
  <function>
    <function_name>get_notes</function_name>
    <function_description>Fetches medical record notes for the current patient from `start_index` to `end_index`.</function_description>
    <required_argument>start_index (int): The starting index for the notes retrieval.</required_argument>
    <required_argument>end_index (int): The ending index for the notes retrieval.</required_argument>
    <returns>table: table: A table of medical record notes.</returns>
    <example_call>get_notes(start_index=value, end_index=value)</example_call>
  </function>
  <function>
    <function_name>get_notes_by_type</function_name>
    <function_description>Fetches medical record notes for the current patient filtered by the note type provided. - Here is the underlying table schema: - Table: notes_data - Columns: id, date, note_type, note_content, source_url - Distinct note types (can change on an ad-hoc basis): "Social Work Screen Comments", "Review of Systems Documentation", "Social Work Clinical Assessment", "PT Precaution", "ICU Weekly Summary Nursing", "ICU Progress (Systems) Nursing", "Central Vascular Catheter Procedure", "Procedure Note", "Genetics Consultation", "Subjective Statement PT", "NICU Admission MD", "General Surgery ICU Progress MD", "Case Management Planning", "Lactation Support Consultation", "Final", "RN Shift Events", "Occupational Therapy Inpatient", "Education Topic Details", "Lab Order/Specimen Not Received Notify", "Report", "cm reason for admission screening tool", "Chief Complaint PT", "Echocardiogram Note", "Assessment and Plan - No Dx", "History of Present Illness Documentation", "Powerplan Not Completed Notification", "PT Treatment Recommendations", "Gram", "Surgery - Patient Summary", "Reason for Referral PT", "Development Comments", "Chaplaincy Inpatient", "Nutrition Consultation", "ICU Admission Nursing", "Inpatient Nursing", "Endocrinology Consultation", "Case Management Note", "Social Work Inpatient Confidential", "General Surgery Admission MD", "Nursing Admission Assessment.", "Hospital Course", "NICU Progress MD", "Physical Examination Documentation", "General Surgery Inpatient MD", "Preliminary Report", "NICU Note Overall Impression"  Returns: table: A table of medical record notes.</function_description>
    <required_argument>type (str): The type of note to be retrieved.</required_argument>
    <returns>table: table: A table of medical record notes.</returns>
    <example_call>get_notes_by_type(type=value)</example_call>
  </function>
  <function>
    <function_name>get_labs</function_name>
    <function_description>Fetches lab data for the current patient from `start_index` to `end_index`. - Table: lab_data - Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high - Distinct lab values (can change on an ad-hoc basis: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"  Returns: table: A table of medical record lab results.</function_description>
    <required_argument>start_index (int): The starting index for the lab data retrieval.</required_argument>
    <required_argument>end_index (int): The ending index for the lab data retrieval.</required_argument>
    <returns>table: table: A table of medical record lab results.</returns>
    <example_call>get_labs(start_index=value, end_index=value)</example_call>
  </function>
  <function>
    <function_name>get_labs_by_type</function_name>
    <function_description>Fetches lab data for the current patient filtered by the lab type provided. - Table: lab_data - Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high - Distinct lab values (can change on an ad-hoc basis: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"  Returns: table: A table of medical record lab results.</function_description>
    <required_argument>type (str): The type of lab to be retrieved.</required_argument>
    <returns>table: table: A table of medical record lab results.</returns>
    <example_call>get_labs_by_type(type=value)</example_call>
  </function>
  <function>
    <function_name>get_count_notes</function_name>
    <function_description>Returns the total count of medical record notes for the current patient.</function_description>
    <returns>int: int: The total count of medical record notes.</returns>
    <example_call>get_count_notes()</example_call>
  </function>
  <function>
    <function_name>get_count_labs</function_name>
    <function_description>Returns the total count of lab records for the current patient.</function_description>
    <returns>int: int: The total count of lab records.</returns>
    <example_call>get_count_labs()</example_call>
  </function>
</functions>


Note that the function arguments have been listed in the order that they should be passed into the function.

Do not modify or extend the provided functions under any circumstances. For example, calling get_current_temp() with additional parameters would be considered modifying the function which is not allowed. Please use the functions only as defined. 

DO NOT use any functions that I have not equipped you with.

To call a function, output <function_call>insert specific function</function_call>. You will receive a <function_result> in response to your call that contains information that you can use to better answer the question.

Here is an example of how you would correctly answer a question using a <function_call> and the corresponding <function_result>. Notice that you are free to think before deciding to make a <function_call> in the <scratchpad>:

<example>
<functions>
<function>
<function_name>run_sql</function_name>
<function_description>Queries medical record notes for current patient. Here's the schema of the database as well as some distinct key values from within it

Table: lab_data
Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high
Table: notes_data
Columns: id, date, note_type, note_content, source_url
Selectable lab values: "Lysine Level", "Oxygen dissociation p50, Capillary", "Phenylalanine Level", "Leukocytes, Urinalysis", "Hemoglobin", "Aspartic Acid Level", "Triglycerides", "Ovalocytes, RBC", "Vancomycin Level, Trough/Pre", "Myelocyte", "Magnesium", "Lactic Acid, Whole Blood", "Bicarb Arterial", "Platelet", "Albumin", "Reflex Sysmex", "Beta-Hydroxybutyric Acid", "Glutamine Level", "Proline Level", "Taurine Level", "Absolute Phagocyte Count", "Chloride", "Blood Culture Routine, Aerobic", "pO2 Venous", "Protein, Urinalysis", "ALT", "Cortisol", "Nitrite,   Urinalysis", "Tryptophan Level", "Neutrophil/Band", "Metamyelocyte", "Carnitine Free/Total", "Immature Reticulocyte Fraction", "pCO2 Venous", "pCO2 Capillary", "Sodium", "Cystine Level", "LDH (Lactate Dehydrogenase)", "Monocyte", "Glucose, Urinalysis", "pH Arterial", "Absolute Eosinophil Count", "RBC", "Bicarb Capillary", "Newborn Screen Result", "Creatinine", "Valine Level", "MPV", "Serine Level", "CO2", "Absolute Basophil Count", "Specific Gravity, Urinalysis", "MCHC", "Leucine Level", "Tyrosine Level", "Glucose Level", "Calcium Ionized", "Absolute Lymphocyte Count", "Lymphocyte", "pH Capillary", "Oxygen dissociation p50, Arterial", "Ketone, Urinalysis", "Glutamic Acid Level", "Anisocytosis, RBC", "Hydroxyproline Level", "Reticulocyte %", "Final", "pH Venous", "Target Cells, RBC", "Ketone Qualitative Source, Other Fluid", "Promyelocyte", "Basophil", "Poikilocytosis, RBC", "Immature Platelet Fraction", "RBC Morph", "Atypical Lymphocyte", "Elliptocytosis, RBC", "O2Sat Arterial", "Blast", "Microcytosis, RBC", "Anion Gap, Whole Blood", "Total Protein", "Potassium", "Methionine Level", "Glycine Level", "Sodium, Whole Blood", "Stomatocytes, RBC", "WBC", "Prolymphocyte", "Alkaline Phosphatase", "Isoleucine Level", "Arginine Level", "Chloride, Whole Blood", "Anion Gap", "Hematocrit", "pO2 Capillary", "Urobilinogen,   Urinalysis", "Asparagine Level", "MCV", "Bilirubin, Urinalysis", "Alanine Level", "Carnitine Free", "Urine Culture", "Nucleated Red Blood Cell %", "Prealbumin", "O2Sat Capillary", "Ornithine Level", "Absolute Monocyte Count", "Histidine Level", "BUN", "Threonine Level", "Color, Urinalysis", "Insulin Level", "Schistocytes, RBC", "pH, Urinalysis", "MCH", "Bilirubin, Direct", "pO2 Arterial", "Phosphorus", "Calcium", "Human Growth Hormone, Random", "Potassium, Whole Blood", "Macrocytosis, RBC", "Appearance, Urinalysis", "Glucose, Whole Blood", "Blood, Urinalysis", "Ketone Qualitative, Other Fluid", "Citrulline Level", "Carnitine Total", "Nucleated Red Blood Cell Count", "Absolute Neutrophil Count", "Bilirubin, Total", "Reticulocyte Cell Hemoglobin", "Reticulocyte, Absolute", "VRE Culture, Rectal", "Respiratory Culture and Gram Stain", "Red Cell Distribution Width CV", "Bicarb Venous", "Oxygen dissociation p50, Venous", "Eosinophil", "O2 Sat Venous", "MRSA Culture", "pCO2 Arterial"
Selectable note types: "Social Work Screen Comments", "Review of Systems Documentation", "Social Work Clinical Assessment", "PT Precaution", "ICU Weekly Summary Nursing", "ICU Progress (Systems) Nursing", "Central Vascular Catheter Procedure", "Procedure Note", "Genetics Consultation", "Subjective Statement PT", "NICU Admission MD", "General Surgery ICU Progress MD", "Case Management Planning", "Lactation Support Consultation", "Final", "RN Shift Events", "Occupational Therapy Inpatient", "Education Topic Details", "Lab Order/Specimen Not Received Notify", "Report", "cm reason for admission screening tool", "Chief Complaint PT", "Echocardiogram Note", "Assessment and Plan - No Dx", "History of Present Illness Documentation", "Powerplan Not Completed Notification", "PT Treatment Recommendations", "Gram", "Surgery - Patient Summary", "Reason for Referral PT", "Development Comments", "Chaplaincy Inpatient", "Nutrition Consultation", "ICU Admission Nursing", "Inpatient Nursing", "Endocrinology Consultation", "Case Management Note", "Social Work Inpatient Confidential", "General Surgery Admission MD", "Nursing Admission Assessment.", "Hospital Course", "NICU Progress MD", "Physical Examination Documentation", "General Surgery Inpatient MD", "Preliminary Report", "NICU Note Overall Impression"
When querying by date, always use today's date and don't use database date functions.
</function_description>
<required_argument>query (str): valid SQL query.</required_argument>
<returns> table: result of sql query in tabular format</returns>
<raises>ValueError: if the sql is invalid.</raises>
<example_call>run_sql(query="SELECT * FROM notes_data")</example_call>
</function>
</functions>

<question>What labs has the patient done in the past??</question>

<scratchpad>I do not have access to the lab history of the patient so I should use a function to gather more information to answer this question. 

I have been equipped with the function run_sql that runs sql on our database so I should use that to gather more information.

There is a table lab_data with columns
Columns: id, date, source, lab, value, units, normal_low, normal_high, critical_low, critical_high

I have double checked and made sure that I have been provided the run_sql function.
</scratchpad>

<function_call>run_sql(query=''' 
SELECT
    lab,
    COUNT(*) AS lab_count,
    MAX(date) AS latest_date
FROM lab_data
GROUP BY lab
ORDER BY lab;
''')</function_call>

<function_result>
| lab                                    |   lab_count | latest_date   |
|:---------------------------------------|------------:|:--------------|
| Absolute Basophil Count                |           5 | 2023-06-09    |
| Absolute Eosinophil Count              |           5 | 2023-06-09    |
| Absolute Lymphocyte Count              |           5 | 2023-06-09    |
| Absolute Monocyte Count                |           5 | 2023-06-09    |
| Absolute Neutrophil Count              |           5 | 2023-06-09    |
| Absolute Phagocyte Count               |           5 | 2023-06-09    |
| Alanine Level                          |           1 | 2023-06-08    |
| Albumin                                |           4 | 2023-06-05    |
| Alkaline Phosphatase                   |           4 | 2023-06-05    |
| ALT                                    |           4 | 2023-06-05
...
</function_result>

<answer>The current temperature in San Francisco is 71 degrees Fahrenheit.</answer>
</example>

Here is another example that utilizes multiple function calls:
<example>
<functions>
<function>
<function_name>get_current_stock_price</function_name>
<function_description>Gets the current stock price for a company</function_description>
<required_argument>symbol (str): The stock symbol of the company to get the price for.</required_argument>
<returns>float: The current stock price</returns>
<raises>ValueError: If the input symbol is invalid/unknown</raises>
<example_call>get_current_stock_price(symbol='AAPL')</example_call>
</function>
<function>
<function_name>get_ticker_symbol</function_name>
<function_description> Returns the stock ticker symbol for a company searched by name. </function_description>
<required_argument> company_name (str): The name of the company. </required_argument>
<returns> str: The ticker symbol for the company stock. </returns>
<raises>TickerNotFound: If no matching ticker symbol is found.</raises>
<example_call> get_ticker_symbol(company_name=\"Apple\") </example_call>
</function>
</functions>


<question>What is the current stock price of General Motors?</question>

<scratchpad>
To answer this question, I will need to:
1. Get the ticker symbol for General Motors using the get_ticker_symbol() function. 
2. Use the returned ticker symbol to get the current stock price using the get_current_stock_price() function.

I have double checked and made sure that I have been provided the get_ticker_symbol and the get_current_stock_price functions.
</scratchpad>

<function_call>get_ticker_symbol(company_name=\"General Motors\")</function_call>

<function_result>GM</function_result>

<function_call>get_current_stock_price(symbol=\"GM\")</function_call>

<function_result>38.50</function_result>

<answer>
The current stock price of General Motors is $38.50.
</answer>
</example>

Here is an example that shows what to do in the case of an error:
<example>
<functions>
<function>
<function_name>get_current_stock_price</function_name>
<function_description>Gets the current stock price for a company</function_description>
<required_argument>symbol (str): The stock symbol of the company to get the price for.</required_argument>
<returns>float: The current stock price</returns>
<example_call>get_current_stock_price(symbol='AAPL')</example_call>
</function>
<function>
<function_name>get_ticker_symbol</function_name>
<function_description> Returns the stock ticker symbol for a company searched by name. </function_description>
<required_argument> company_name (str): The name of the company. </required_argument>
<returns> str: The ticker symbol for the company stock. </returns>
<raises>TickerNotFound: If no matching ticker symbol is found.</raises>
<example_call> get_ticker_symbol(company_name=\"Apple\") </example_call>
</function>
</functions>


<question>What is the current stock price of The General Motors Company LLC?</question>

<scratchpad>
To answer this question, I will need to:
1. Get the ticker symbol for The General Motors Company LLC using the get_ticker_symbol() function. 
2. Use the returned ticker symbol to get the current stock price using the get_current_stock_price() function.

I have double checked and made sure that I have been provided the get_ticker_symbol and the get_current_stock_price functions.
</scratchpad>

<function_call>get_ticker_symbol(company_name=\"The General Motors Company LLC\")</function_call>

<error>TickerNotFound: If no matching ticker symbol is found.</error>

<scratchpad>The get_ticker_symbol(company_name=\"The General Motors Company LLC\") call raised a TickerNotFound: If no matching ticker symbol is found error indicating that the provided str did not return a matching ticker symbol. I should retry the function using another name variation of the company.</scratchpad> 

<function_call>get_ticker_symbol(company_name=\"General Motors\")</function_call>

<function_result>GM</function_result>

<function_call>get_current_stock_price(symbol=\"GM\")</function_call>

<function_result>38.50</function_result>

<answer>
The current stock price of General Motors is $38.50.
</answer>
</example>

Notice in this example, the initial function call raised an error. Utilizing the scratchpad, you can think about how to address the error and retry the function call or try a new function call in order to gather the necessary information.

Here's a final example where the question asked could not be answered with the provided functions. In this example, notice how you respond without using functions that are not provided to you.

<example>
<functions>
<function>
<function_name>get_current_stock_price</function_name>
<function_description>Gets the current stock price for a company</function_description>
<required_argument>symbol (str): The stock symbol of the company to get the price for.</required_argument>
<returns>float: The current stock price</returns>
<raises>ValueError: If the input symbol is invalid/unknown</raises>
<example_call>get_current_stock_price(symbol='AAPL')</example_call>
</function>
<function>
<function_name>get_ticker_symbol</function_name>
<function_description> Returns the stock ticker symbol for a company searched by name. </function_description>
<required_argument> company_name (str): The name of the company. </required_argument>
<returns> str: The ticker symbol for the company stock. </returns>
<raises>TickerNotFound: If no matching ticker symbol is found.</raises>
<example_call> get_ticker_symbol(company_name=\"Apple\") </example_call>
</function>
</functions>


<question>What is the current exchange rate for USD to Euro?</question>

<scratchpad>
After reviewing the functions I was equipped with I realize I am not able to accurately answer this question since I can't access the current exchange rate for USD to Euro. Therefore, I should explain to the user I cannot answer this question.
</scratchpad>

<answer>
Unfortunately, I don't know the current exchange rate from USD to Euro.
</answer>
</example>

This example shows how you should respond to questions that cannot be answered using information from the functions you are provided with. Remember, DO NOT use any functions that I have not provided you with.

Remember, your goal is to answer the user's question to the best of your ability, using only the function(s) provided to gather more information if necessary to better answer the question. 

Do not modify or extend the provided functions under any circumstances. For example, calling get_current_temp() with additional parameters would be modifying the function which is not allowed. Please use the functions only as defined. 

The result of a function call will be added to the conversation history as an observation. Never make up the function result, just open the tag and let the Human insert the resul. If necessary, you can make multiple function calls and use all the functions I have equipped you with. Let's create a plan and then execute the plan. Double check your plan to make sure you don't call any functions that I haven't provided. Always return your final answer within  <answer></answer> tags and use markdown format.


The question to answer is <question>{question}</question>
    
    
    {AI_PROMPT}<scratchpad> I understand I cannot use functions that have not been provided to me to answer this question.
    """
    return INITIAL_PROMPT





app = Flask(__name__)

@app.route('/conduct_chat', methods=['POST'])
def conduct_chat_endpoint():
    initial_messages = request.json.get('initial_messages')
    last_message = initial_messages[-1]
    question = last_message['content']
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
                    function_call_match = re.search(r"<function_call>\s*(.*?)\s*</function_call>", buffer, re.DOTALL)
                    function_call_content = function_call_match.group(1) if function_call_match else None
                    print(function_call_content)

                    yield '**⚙️ Calling function**\n\n'
        
                    result = eval(function_call_content)
                    current_prompt = current_prompt + buffer + "<function_result>" + result + "</function_result>"
                    break
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    return Response(conduct_chat(), headers=headers)

if __name__ == '__main__':
    app.run(port=8000)
