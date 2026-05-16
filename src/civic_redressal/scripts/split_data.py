import pandas as pd
import os
from sklearn.model_selection import train_test_split

# Configuration
INPUT_CSV = "../data/icmyc-2019-2022.csv"
OUTPUT_DIR = "./data"
TRAIN_OUTPUT = os.path.join(OUTPUT_DIR, "train.csv")
VAL_OUTPUT = os.path.join(OUTPUT_DIR, "val.csv")
TEST_OUTPUT = os.path.join(OUTPUT_DIR, "test.csv")

RANDOM_STATE = 42
TARGET_COLUMNS = ["category_id", "category_title", "sub_category_id", "sub_category_title", "civic_agency_id", "civic_agency_title"]

def main():
    """Load data, split into train/val/test, and save to CSV files."""
    
    # Load the CSV file with proper encoding handling
    print(f"Loading data from {INPUT_CSV}...")
    try:
        # Try UTF-8 first
        df = pd.read_csv(INPUT_CSV, encoding='utf-8')
    except UnicodeDecodeError:
        # Try latin-1 as fallback
        print("UTF-8 encoding failed, trying latin-1...")
        df = pd.read_csv(INPUT_CSV, encoding='latin-1')
    
    print(f"Total rows loaded: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Rename Bangalore Traffic Police to BTP
    df["civic_agency_title"] = df["civic_agency_title"].replace("Bangalore Traffic Police", "BTP")
    print(f"\nRenamed 'Bangalore Traffic Police' to 'BTP'")
    
    # Rename Bruhat Bengaluru Mahanagara Palike to BBMP
    df["civic_agency_title"] = df["civic_agency_title"].replace("Bruhat Bengaluru Mahanagara Palike", "BBMP")
    print(f"Renamed 'Bruhat Bengaluru Mahanagara Palike' to 'BBMP'")
    
    # Check for rows with ANY NULL values in target columns
    df['has_null_target'] = df[TARGET_COLUMNS].isna().any(axis=1)
    null_count = df['has_null_target'].sum()
    non_null_count = len(df) - null_count
    print(f"\nRows with ANY NULL in target columns: {null_count}")
    print(f"Rows with ALL target columns filled: {non_null_count}")
    
    # Separate NULL and non-NULL rows
    df_null = df[df['has_null_target']].copy()
    df_non_null = df[~df['has_null_target']].copy()
    
    # Drop temporary column
    df_non_null = df_non_null.drop('has_null_target', axis=1)
    df_null = df_null.drop('has_null_target', axis=1)
    
    print(f"\nClass distribution in non-NULL rows (civic_agency_title):")
    print(df_non_null["civic_agency_title"].value_counts())
    
    # Split non-NULL rows: 70% train, 30% temp (for val/test)
    print(f"\nSplitting non-NULL rows (70% train, 30% temp for val/test)...")
    
    # Create composite key for stratification across all target columns
    df_non_null['stratify_key'] = (
        df_non_null['category_id'].astype(str) + '_' +
        df_non_null['category_title'].astype(str) + '_' +
        df_non_null['sub_category_id'].astype(str) + '_' +
        df_non_null['sub_category_title'].astype(str) + '_' +
        df_non_null['civic_agency_id'].astype(str) + '_' +
        df_non_null['civic_agency_title'].astype(str)
    )
    
    # Check if stratification is possible (each class needs at least 2 samples for split)
    min_samples_per_class = df_non_null['stratify_key'].value_counts().min()
    use_stratify = min_samples_per_class >= 2
    
    if not use_stratify:
        print(f"Warning: Some classes have only 1 sample. Using random split without stratification.")
        df_train, df_temp = train_test_split(
            df_non_null,
            test_size=0.30,
            random_state=RANDOM_STATE
        )
    else:
        df_train, df_temp = train_test_split(
            df_non_null,
            test_size=0.30,
            stratify=df_non_null['stratify_key'],
            random_state=RANDOM_STATE
        )
    
    # Split temp into 50/50 for val/test (15% each of non-NULL)
    print(f"Splitting temp into validation/test (50/50)...")
    
    # Check if stratification is possible for temp split
    min_samples_in_temp = df_temp['stratify_key'].value_counts().min()
    use_stratify_temp = min_samples_in_temp >= 2
    
    if not use_stratify_temp:
        df_val_non_null, df_test = train_test_split(
            df_temp,
            test_size=0.50,
            random_state=RANDOM_STATE
        )
    else:
        df_val_non_null, df_test = train_test_split(
            df_temp,
            test_size=0.50,
            stratify=df_temp['stratify_key'],
            random_state=RANDOM_STATE
        )
    
    # Remove temporary stratify_key column
    df_train = df_train.drop('stratify_key', axis=1)
    df_val_non_null = df_val_non_null.drop('stratify_key', axis=1)
    df_test = df_test.drop('stratify_key', axis=1)
    
    # Add NULL rows to test
    print(f"Adding {null_count} NULL rows to test set...")
    df_test = pd.concat([df_test, df_null], ignore_index=True)
    
    # Verify splits
    print(f"\n{'='*60}")
    print(f"SPLIT SUMMARY:")
    print(f"{'='*60}")
    print(f"Train set size: {len(df_train)} ({len(df_train)/len(df)*100:.1f}% of total)")
    print(f"Validation set size: {len(df_val_non_null)} ({len(df_val_non_null)/len(df)*100:.1f}% of total)")
    print(f"Test set size: {len(df_test)} ({len(df_test)/len(df)*100:.1f}% of total)")
    print(f"  - Non-NULL rows: {len(df_test) - null_count}")
    print(f"  - NULL rows: {null_count}")
    print(f"Total: {len(df_train) + len(df_val_non_null) + len(df_test)} (should be {len(df)})")
    print(f"{'='*60}\n")
    
    # Verify no data loss
    assert len(df_train) + len(df_val_non_null) + len(df_test) == len(df), "Data loss detected!"
    
    # Verify all NULL rows are in test
    df_test_null_check = df_test[TARGET_COLUMNS].isna().any(axis=1).sum()
    assert df_test_null_check == null_count, "Not all NULL rows in test!"
    
    # Verify stratification by checking class distribution
    print(f"Class distribution comparison (%):")
    print(f"\nTrain set (civic_agency_title):")
    print((df_train["civic_agency_title"].value_counts(normalize=True) * 100).round(2))
    print(f"\nTest set (civic_agency_title):")
    print((df_test["civic_agency_title"].value_counts(normalize=True) * 100).round(2))
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Columns to remove from all files
    columns_to_remove = ["complaint_status_title", "count", "comment_count"]
    
    # Remove columns from all dataframes
    df_train = df_train.drop(columns=[col for col in columns_to_remove if col in df_train.columns])
    df_val_non_null = df_val_non_null.drop(columns=[col for col in columns_to_remove if col in df_val_non_null.columns])
    df_test = df_test.drop(columns=[col for col in columns_to_remove if col in df_test.columns])
    
    # Remove target columns from val and test files (keep only in train)
    df_val_non_null = df_val_non_null.drop(columns=[col for col in TARGET_COLUMNS if col in df_val_non_null.columns])
    df_test = df_test.drop(columns=[col for col in TARGET_COLUMNS if col in df_test.columns])
    
    # Save to CSV files
    print(f"\nSaving splits to {OUTPUT_DIR}...")
    df_train.to_csv(TRAIN_OUTPUT, index=False)
    print(f"✓ Saved {len(df_train)} rows to {TRAIN_OUTPUT}")
    
    df_val_non_null.to_csv(VAL_OUTPUT, index=False)
    print(f"✓ Saved {len(df_val_non_null)} rows to {VAL_OUTPUT}")
    
    df_test.to_csv(TEST_OUTPUT, index=False)
    print(f"✓ Saved {len(df_test)} rows to {TEST_OUTPUT}")
    
    print(f"\n{'='*60}")
    print(f"Data splitting complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
