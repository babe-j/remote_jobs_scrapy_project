import pandas as pd
import os
import re

# ==========================================================
# STEP 1: Load keywords mapping for classification
# ==========================================================

# Read the keyword-to-job section CSV file
df_job_section = pd.read_csv(r"C:\Users\user\scrapy_project2\jobs\Himalayas and Upwork\Upwork_keywords.csv")

# Normalize the 'Keywords' column: lowercase and strip extra spaces
df_job_section['Keywords'] = df_job_section['Keywords'].str.lower().str.strip()

# Create a dictionary mapping: keyword → JobSection
# Example: {'python': 'Programming', 'copywriting': 'Writing'}
key_per_section = dict(zip(df_job_section['Keywords'], df_job_section['JobSection']))


# ==========================================================
# STEP 2: Helper function to split job titles into tags
# ==========================================================

def jobtitle_split(title: str, fallback=None):
    """
    Splits a job title (or fallback value if title is NaN) into lowercase tags.
    Tags are separated by commas for easy matching.
    
    Parameters:
        title (str): The job title or keyword string.
        fallback (str): A backup title to use if 'title' is 'nan'.
    
    Returns:
        str: Comma-separated list of words/tags.
    """
    if title != 'nan':
        # Split on spaces, ampersands, commas, or hyphens
        job_split = re.split(r'[\s&,\-]+', title.lower())
    else:
        # If title is 'nan', use fallback
        job_split = re.split(r'[\s&,\-]+', fallback.lower())
    
    # Join words into a comma-separated string
    job_tags = (',').join(job_split)
    return job_tags


# ==========================================================
# STEP 3: Helper function to match tags to job section
# ==========================================================

def add_matching_job_section(title_list, fallback=None):
    """
    Matches tags from a title to the most relevant job section using the keyword dictionary.
    
    Parameters:
        title_list (str): Comma-separated tags from the job title.
        fallback (str): Value to return if no match is found.
    
    Returns:
        str: Best matching job section or the fallback value.
    """
    if pd.isna(title_list):
        return None

    scores = {}  # Dictionary to store match counts per job section
    tags = title_list.split(',')

    for tag in tags:
        if tag == '':
            continue
        for kw, js in key_per_section.items():
            # Check if the tag is part of a keyword
            if tag in kw:
                scores[js] = scores.get(js, 0) + 1

    # If there are matches, return the section with the highest score
    if scores:
        best_matching_section = max(scores, key=scores.get)
        return best_matching_section
    else:
        # If no matches found, return fallback
        return fallback


# ==========================================================
# STEP 4: Create output folder for cleaned datasets
# ==========================================================

os.makedirs('cleaned_dataset', exist_ok=True)


# ==========================================================
# STEP 5: Clean Upwork dataset
# ==========================================================

try:
    # Load Upwork dataset
    df_upwork = pd.read_csv('upwork_jobs.csv')

    # Convert 'Tags' column to string
    df_upwork['Tags'] = df_upwork['Tags'].astype(str)

    # Create 'TitleList' column from 'Tags', falling back to 'Title' if needed
    df_upwork['TitleList'] = df_upwork.apply(lambda row: jobtitle_split(row['Tags'], row['Title']), axis=1)

    # Remove unused columns
    df_upwork = df_upwork.drop(['DatePosted', 'Duration', 'Price', 'JobLink', 'Tags'], axis=1)

    # Standardize job type: convert all "Hourly..." variants to "Hourly"
    df_upwork['JobType'] = df_upwork['JobType'].str.replace(r'^Hourly.*', 'Hourly', case=False, regex=True)

    # Clean job titles:
    df_upwork['Title'] = (
        df_upwork['Title']
          .str.strip()  # Remove leading/trailing spaces
          .str.replace(r'[\[\(\{<]+[^\]\)\}>]*[\]\)\}>]+', '', regex=True)  # Remove bracketed content
          .str.replace(r'^[^a-zA-Z0-9$]+|[^a-zA-Z0-9$]+$', '', regex=True)  # Remove leading/trailing non-alphanumerics
          .str.replace(r'\$.*?[:\-]+', '', regex=True)  # Remove salary info like "$500 - ..."
    )

    # Remove duplicates based on all columns except 'TitleList'
    df_upwork = df_upwork.drop_duplicates([col for col in df_upwork.columns if col != 'TitleList'])

    # Drop rows with any empty strings or NaN values
    df_upwork = df_upwork[df_upwork.apply(lambda row: all(str(x).strip() != "" for x in row), axis=1)].dropna()

    # Assign job category based on title list
    df_upwork['JobCategory'] = df_upwork.apply(lambda row: add_matching_job_section(row['TitleList'], row['Title']), axis=1)

    # Remove the helper column
    df_upwork = df_upwork.drop(['TitleList'], axis=1)

    # Save cleaned dataset
    df_upwork.to_csv('cleaned_dataset/upwork_jobs_cleaned_dataset.csv', index=0)

except Exception as e:
    print(f'Exception: {e}')


# ==========================================================
# STEP 6: Clean Himalayas dataset
# ==========================================================

df_himalayas = pd.read_csv('himalayas_jobs.csv')

# Remove unused columns
df_himalayas = df_himalayas.drop(['DatePosted', 'JobLink'], axis=1)

# Clean job titles
df_himalayas['Title'] = (
    df_himalayas['Title']
      .str.strip()
      .str.replace(r'^1099', '', regex=True)  # Remove leading '1099' contract notation
      .str.replace(r'[\[\(\{<]+[^\]\)\}>]*[\]\)\}>]+', '', regex=True)  # Remove bracketed text
      .str.replace(r'^[^a-zA-Z0-9$]+|[^a-zA-Z0-9$]+$', '', regex=True)  # Remove unwanted leading/trailing chars
      .str.replace(r'\d.*?[\-]+', '', regex=True)  # Remove numeric ranges like "2023-..."
)

# Remove duplicates
df_himalayas = df_himalayas.drop_duplicates()

# Drop rows with any empty strings or NaNs
df_himalayas = df_himalayas[df_himalayas.apply(lambda row: all(str(x).strip() != "" for x in row), axis=1)].dropna()

# Generate list of tags from Title
df_himalayas['TitleList'] = df_himalayas['Title'].apply(jobtitle_split)

# Assign job category
df_himalayas['JobCategory'] = df_himalayas.apply(lambda row: add_matching_job_section(row['TitleList'], row['Title']), axis=1)

# Remove helper column
df_himalayas = df_himalayas.drop(['TitleList'], axis=1)

# Save cleaned dataset
df_himalayas.to_csv('cleaned_dataset/himalayas_jobs_cleaned_dataset.csv', index=False)


# ==========================================================
# STEP 7: Clean RemoteOK dataset
# ==========================================================

df_remote_ok = pd.read_csv('RemoteOK_jobs.csv')

# Remove unused columns
df_remote_ok = df_remote_ok.drop(['JOB_URL', 'DATE_POSTED', 'COMPANY_COUNTRY'], axis=1)

# Remove duplicates
df_remote_ok = df_remote_ok.drop_duplicates()

# Drop rows with any empty strings or NaNs
df_remote_ok = df_remote_ok[df_remote_ok.apply(lambda row: all(str(x).strip() != "" for x in row), axis=1)].dropna()

# Generate list of tags from JOB_NAME
df_remote_ok['JOB_NAME_LIST'] = df_remote_ok['JOB_NAME'].apply(jobtitle_split)

# Assign job category
df_remote_ok['JobCategory'] = df_remote_ok.apply(lambda row: add_matching_job_section(row['JOB_NAME_LIST'], row['JOB_NAME']), axis=1)

# Remove helper column
df_remote_ok = df_remote_ok.drop(['JOB_NAME_LIST'], axis=1)

# Save cleaned dataset
df_remote_ok.to_csv('cleaned_dataset/RemotOK_jobs_cleaned_dataset.csv', index=False)
