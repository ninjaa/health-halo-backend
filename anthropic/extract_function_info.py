import functools
from tabulate import tabulate
from pprint import pprint
import os
import psycopg2
from dotenv import load_dotenv
from anthropic.dict_to_pretty_xml import dict_to_pretty_xml
import re

load_dotenv()


def get_all_tables() -> str:
    """
    Retrieves a string representation of all the tables in a PostgreSQL database using environment variables.

    Returns: str: A string representation of all tables in the database.
    Raises: Exception: If there's any error in connecting or fetching data from the database.
    """
    # Load database configurations from environment variables
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

        # Query to get all tables from the current schema
        cursor.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """)

        tables = cursor.fetchall()

        return [table[0] for table in tables]

    except Exception as e:
        raise e

    finally:
        if connection:
            connection.close()

# some comment


def get_table_schema(table_name: str) -> str:
    """
    Retrieves the schema (structure) of a specific table in a PostgreSQL database using environment variables.

    Arguments:
    table_name (str): The name of the table whose schema is to be retrieved.

    Returns: str: A formatted string representation of the table schema.
    Raises: Exception: If there's any error in connecting or fetching data from the database.
    """
    # Load database configurations from environment variables
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

        # Query to get schema of the table
        cursor.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        """, (table_name,))

        columns = cursor.fetchall()
        schema_repr = [
            f"{col[0]} ({col[1]}){'('+str(col[2])+')' if col[2] else ''} {'NOT NULL' if col[3] == 'NO' else ''}" for col in columns]

        return "\n".join(schema_repr)

    except Exception as e:
        raise e

    finally:
        if connection:
            connection.close()


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


# Get the total count of lab records for the current patient.
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
def run_python(code: "str") -> "str":
    """
    Runs the python code provided and returns the result.

    Raises:
    ValueError: if the code is invalid.

    Returns:
    (bool, str): A tuple containing the success status and the result (if successful) or error (if unsuccessful)
    """
    success = False
    try:
        result = eval(code)
        success = True
    except Exception as e:
        error = str(e)

    return (success, result if success else error)


# Test
# print(run_sql("SELECT * FROM your_table_name LIMIT 5"))


# Sample usage (replace with actual values):
# tables = get_all_tables()
# pprint(tables)
# for table_name in tables:
#     print(table_name)
#     print(get_table_schema(table_name))

# print(run_sql("""
#   WITH LabDates AS (
#       SELECT
#           lab,
#           ARRAY_AGG(date ORDER BY date DESC) AS dates
#       FROM lab_data
#       GROUP BY lab
#   )

#   SELECT
#       l.lab,
#       COUNT(t.id) AS lab_count,
#       MAX(t.date) AS latest_date,
#       l.dates AS lab_dates
#   FROM lab_data t
#   JOIN LabDates l ON t.lab = l.lab
#   GROUP BY l.lab, l.dates
#   ORDER BY l.lab;
#               """))

# print(run_sql("""
# SELECT
#     lab,
#     COUNT(*) AS lab_count,
#     MAX(date) AS latest_date
# FROM lab_data
# GROUP BY lab
# ORDER BY lab;
#               """))
# pprint(functions)
# # Example Usage:
xml_str = dict_to_pretty_xml(functions)
print(xml_str)
