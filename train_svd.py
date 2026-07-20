"""Offline training script for Collaborative Filtering (SVD) model.

This script:
1. Verifies if data/rating_complete.csv exists.
2. Filters out users with less than 50 ratings.
3. Filters out anime not present in anime_dataset.csv.
4. Trains an SVD model using scikit-surprise.
5. Evaluates the model using 80/20 train/test split.
6. Saves the item factors, biases, and ID mapping to data/svd_model.pkl.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import accuracy
import joblib

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RATING_PATH = os.path.join(DATA_DIR, "rating_complete.csv")
ANIME_PATH = os.path.join(DATA_DIR, "anime_dataset.csv")
MODEL_PATH = os.path.join(DATA_DIR, "svd_model.pkl")


def main():
    # Force UTF-8 stdout encoding to prevent Unicode errors on Windows with non-ASCII paths
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    print("=== Collaborative Filtering (SVD) Offline Training ===")

    # 1. Check if rating dataset exists
    if not os.path.exists(RATING_PATH):
        print(f"\n[ERROR] File not found: data/rating_complete.csv")
        print("\nPlease download the 'Anime Recommendation Database 2020' by Hernan4444 from Kaggle:")
        print("URL: https://www.kaggle.com/datasets/hernan4444/anime-recommendation-database-2020")
        print("Extract the 'rating_complete.csv' file and place it in the 'data/' directory.")
        print(f"Expected path: data/rating_complete.csv\n")
        sys.exit(1)

    if not os.path.exists(ANIME_PATH):
        print(f"\n[ERROR] Anime dataset not found at data/anime_dataset.csv.")
        sys.exit(1)

    # 2. Load anime dataset to get valid mal_ids
    print("Loading anime dataset for ID validation...")
    anime_df = pd.read_csv(ANIME_PATH)
    valid_anime_ids = set(anime_df["mal_id"].unique())
    print(f"Loaded {len(valid_anime_ids)} unique anime IDs.")

    # 3. Load ratings dataset
    print("Loading ratings dataset (this might take a minute)...")
    ratings_df = pd.read_csv(RATING_PATH)
    print(f"Total raw ratings: {len(ratings_df)}")

    # 4. Filter ratings
    # 4.1 Filter anime present in anime_dataset.csv
    ratings_df = ratings_df[ratings_df["anime_id"].isin(valid_anime_ids)]
    print(f"Ratings after filtering valid anime: {len(ratings_df)}")

    # 4.2 Filter users with >= 50 ratings
    print("Filtering users with >= 50 ratings to reduce noise and memory usage...")
    user_counts = ratings_df["user_id"].value_counts()
    active_users = user_counts[user_counts >= 50].index
    ratings_df = ratings_df[ratings_df["user_id"].isin(active_users)]
    print(f"Ratings after user filtering: {len(ratings_df)}")
    print(f"Unique users: {ratings_df['user_id'].nunique()}")
    print(f"Unique anime with ratings: {ratings_df['anime_id'].nunique()}")

    # 5. Build surprise dataset
    print("Preparing surprise dataset...")
    reader = Reader(rating_scale=(1, 10))
    # surprise expects columns in order: user, item, rating
    data = Dataset.load_from_df(ratings_df[["user_id", "anime_id", "rating"]], reader)

    # 6. Evaluate with 80/20 split
    print("Evaluating model with 80/20 train/test split...")
    train_eval, test_eval = train_test_split(data, test_size=0.2, random_state=42)
    eval_model = SVD(n_factors=50, n_epochs=20, random_state=42)
    eval_model.fit(train_eval)
    predictions = eval_model.test(test_eval)
    rmse = accuracy.rmse(predictions)
    print(f"Validation RMSE: {rmse:.4f}")

    # 7. Train on FULL filtered dataset
    print("Training SVD model on the full filtered dataset...")
    full_trainset = data.build_full_trainset()
    final_model = SVD(n_factors=50, n_epochs=20, random_state=42)
    final_model.fit(full_trainset)

    # 8. Extract item factors and mappings to keep model light (RAM/disk optimized)
    print("Extracting SVD item factors & biases...")
    raw_to_inner = {}
    inner_to_raw = {}
    
    for inner_id in full_trainset.all_items():
        raw_id = int(full_trainset.to_raw_iid(inner_id))
        raw_to_inner[raw_id] = inner_id
        inner_to_raw[inner_id] = raw_id

    # final_model.qi is of shape (n_items, n_factors)
    # final_model.bi is of shape (n_items,)
    model_data = {
        "global_mean": float(full_trainset.global_mean),
        "item_factors": final_model.qi,
        "item_biases": final_model.bi,
        "raw_to_inner": raw_to_inner,
        "inner_to_raw": inner_to_raw,
        "rmse": float(rmse),
        "n_factors": 50
    }

    # Save to pkl using joblib for fast serialization of numpy arrays
    print("Saving lightweight model to data/svd_model.pkl...")
    joblib.dump(model_data, MODEL_PATH, compress=3)
    file_size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"Model saved successfully. File size: {file_size_mb:.2f} MB")
    print("Offline training complete!")


if __name__ == "__main__":
    main()
