"""Collaborative Filtering (SVD) recommender module.

Uses trained SVD item factors to compute:
1. Item-item similarity in latent space.
2. User recommendations for new profiles using a pseudo-user vector approach.
"""

import os
import numpy as np
import joblib


class CollabRecommender:
    def __init__(self, model_path, dataset_mal_ids):
        """Khởi tạo CollabRecommender.
        
        model_path: đường dẫn tới file .pkl chứa item factors và biases.
        dataset_mal_ids: danh sách các mal_id có trong anime_dataset.csv để lọc.
        """
        self.model_path = model_path
        self.dataset_mal_ids = set(int(m) for m in dataset_mal_ids)
        self.is_ready = False
        
        # Các tham số của model SVD
        self.global_mean = 0.0
        self.item_factors = None
        self.item_biases = None
        self.raw_to_inner = {}
        self.inner_to_raw = {}
        self.valid_mal_ids = set()
        
        self.load_model()
        
    def load_model(self):
        """Load model SVD đã lưu."""
        if not os.path.exists(self.model_path):
            print("[CollabRecommender] Model file not found at data/svd_model.pkl. Collaborative recommendations disabled.")
            return
            
        try:
            model_data = joblib.load(self.model_path)
            self.global_mean = model_data.get("global_mean", 0.0)
            self.item_factors = model_data.get("item_factors")
            self.item_biases = model_data.get("item_biases")
            self.raw_to_inner = model_data.get("raw_to_inner", {})
            self.inner_to_raw = model_data.get("inner_to_raw", {})
            
            # Chỉ lấy các anime ID có trong cả model và dataset hiện tại
            model_raw_ids = set(int(m) for m in self.raw_to_inner.keys())
            self.valid_mal_ids = model_raw_ids.intersection(self.dataset_mal_ids)
            
            if len(self.valid_mal_ids) > 0:
                self.is_ready = True
                print(f"[CollabRecommender] Loaded SVD model. Matched {len(self.valid_mal_ids)} anime items.")
            else:
                print("[CollabRecommender] SVD model loaded but 0 items matched dataset. Collaborative recommendations disabled.")
        except Exception as e:
            print("[CollabRecommender] Error loading model. Collaborative recommendations disabled.")

    def similar_items(self, target_mal_id, n=12):
        """Tìm các anime tương tự bằng cách tính cosine similarity trong không gian ẩn SVD."""
        if not self.is_ready or int(target_mal_id) not in self.valid_mal_ids:
            return []
            
        try:
            target_inner = self.raw_to_inner[int(target_mal_id)]
            target_vec = self.item_factors[target_inner]
            
            # Tính norm
            norms = np.linalg.norm(self.item_factors, axis=1)
            target_norm = np.linalg.norm(target_vec)
            
            if target_norm == 0:
                return []
                
            # Tránh chia cho 0
            norms[norms == 0] = 1e-9
            
            # Tích vô hướng và cosine similarity
            dots = np.dot(self.item_factors, target_vec)
            sims = dots / (norms * target_norm)
            
            # Lấy top N (loại trừ chính target_mal_id)
            sorted_inners = np.argsort(-sims)
            
            similar_mal_ids = []
            for inner in sorted_inners:
                raw_id = self.inner_to_raw[inner]
                if raw_id == int(target_mal_id):
                    continue
                if raw_id in self.valid_mal_ids:
                    similar_mal_ids.append(raw_id)
                    if len(similar_mal_ids) >= n:
                        break
                        
            return similar_mal_ids
        except Exception as e:
            print(f"[CollabRecommender] Error in similar_items: {e}")
            return []

    def predict_for_user_profile(self, finished_mal_ids, n=12):
        """Dự đoán anime cho user mới dựa trên gu của các anime đã xem (pseudo-user).
        
        pseudo_user_factor = mean(item_factors của các anime đã xem).
        predicted_score = global_mean + item_bias + dot(item_factor, pseudo_user_factor).
        """
        if not self.is_ready:
            return []
            
        try:
            valid_watched = [int(m) for m in finished_mal_ids if int(m) in self.valid_mal_ids]
            if not valid_watched:
                return []
                
            # Lấy inner indices
            watched_inners = [self.raw_to_inner[m] for m in valid_watched]
            watched_factors = self.item_factors[watched_inners]
            
            # Tính pseudo user vector
            pseudo_user_factor = np.mean(watched_factors, axis=0)
            
            # Dự đoán scores cho toàn bộ anime
            predicted_scores = self.global_mean + self.item_biases + np.dot(self.item_factors, pseudo_user_factor)
            
            # Sắp xếp giảm dần
            sorted_inners = np.argsort(-predicted_scores)
            
            exclude_set = set(int(m) for m in finished_mal_ids)
            recommendations = []
            
            for inner in sorted_inners:
                raw_id = self.inner_to_raw[inner]
                if raw_id in exclude_set:
                    continue
                if raw_id in self.valid_mal_ids:
                    recommendations.append({
                        "mal_id": raw_id,
                        "score": float(predicted_scores[inner])
                    })
                    if len(recommendations) >= n:
                        break
                        
            return recommendations
        except Exception as e:
            print(f"[CollabRecommender] Error in predict_for_user_profile: {e}")
            return []
