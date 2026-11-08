import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
import os
from datetime import datetime
import random

MODEL_PATH = "fraud_model.pkl"

class SeedFraudDetector:
    def __init__(self):
        self.model = None
        self.feature_columns = ['quantity', 'days_to_expiry', 'split_count', 'transfer_frequency', 'batch_age_days', 'geo_distance']
        self.is_trained = False
        self.min_train_score = -0.5
        self.max_train_score = 0.5

    def generate_synthetic_data(self, n=600):
        """Generate synthetic seed supply chain data for training."""
        np.random.seed(42)
        n_fraud = int(n * 0.25)
        n_normal = n - n_fraud

        # Normal patterns: reasonable quantities, good expiry, few splits
        data_normal = {
            'quantity': np.random.uniform(50, 5000, n_normal),         # 50g to 5kg
            'days_to_expiry': np.random.uniform(90, 730, n_normal),    # 3 months to 2 years
            'split_count': np.random.randint(0, 3, n_normal),          # 0-2 splits
            'transfer_frequency': np.random.randint(0, 4, n_normal),   # 0-3 transfers
            'batch_age_days': np.random.uniform(0, 180, n_normal),     # 0-6 months old
            'geo_distance': np.random.uniform(0, 200, n_normal),       # 0-200 km
        }

        # Fraudulent patterns: bulk quantities, near-expiry, excessive splits, rapid transfers
        data_fraud = {
            'quantity': np.random.uniform(8000, 50000, n_fraud),       # Suspiciously large
            'days_to_expiry': np.random.uniform(0, 30, n_fraud),       # Near expiry
            'split_count': np.random.randint(5, 20, n_fraud),          # Many splits
            'transfer_frequency': np.random.randint(5, 15, n_fraud),   # Rapid transfers
            'batch_age_days': np.random.uniform(300, 700, n_fraud),    # Very old batches
            'geo_distance': np.random.uniform(500, 2000, n_fraud),     # Cross-country
        }

        df = pd.concat([pd.DataFrame(data_normal), pd.DataFrame(data_fraud)], ignore_index=True)
        return df

    def train(self):
        print("GENERATING SYNTHETIC SEED DATA...")
        df = self.generate_synthetic_data()

        print("TRAINING ISOLATION FOREST MODEL FOR SEED FRAUD...")
        self.model = IsolationForest(n_estimators=100, contamination=0.25, random_state=42)
        self.model.fit(df[self.feature_columns])

        scores = self.model.decision_function(df[self.feature_columns])
        self.min_train_score = scores.min()
        self.max_train_score = scores.max()

        self.model.min_score_ = self.min_train_score
        self.model.max_score_ = self.max_train_score

        joblib.dump(self.model, MODEL_PATH)
        self.is_trained = True
        print(f"SEED FRAUD MODEL SAVED TO {MODEL_PATH}")

    def load(self):
        # Always retrain for seed-specific model
        self.train()

    def predict(self, data):
        """
        Predict fraud score for a seed transaction.
        Returns: (fraud_score 0-1, risk_level, reasons[])
        """
        if not self.is_trained:
            self.load()

        quantity = data.get('quantity', 0)
        days_to_expiry = data.get('days_to_expiry', 365)
        split_count = data.get('split_count', 0)
        transfer_frequency = data.get('transfer_frequency', 0)
        batch_age_days = data.get('batch_age_days', 0)
        geo_distance = data.get('geo_distance', 0)

        # Prepare model input
        input_data = {
            'quantity': quantity,
            'days_to_expiry': days_to_expiry,
            'split_count': split_count,
            'transfer_frequency': transfer_frequency,
            'batch_age_days': batch_age_days,
            'geo_distance': geo_distance,
        }
        input_df = pd.DataFrame([input_data])

        # Get raw model score
        raw_score = self.model.decision_function(input_df[self.feature_columns])[0]

        # Normalize: IF returns positive for inliers, negative for outliers
        range_span = self.max_train_score - self.min_train_score
        if range_span == 0:
            range_span = 1
        norm_score = (raw_score - self.min_train_score) / range_span
        model_score = 1.0 - np.clip(norm_score, 0, 1)  # Invert: 1 = fraud

        # Rule-based boosters
        expiry_risk = 0.0
        if days_to_expiry < 7:
            expiry_risk = 0.8
        elif days_to_expiry < 30:
            expiry_risk = 0.4
        elif days_to_expiry < 90:
            expiry_risk = 0.1

        split_risk = min(split_count / 10, 1.0)
        transfer_risk = min(transfer_frequency / 8, 1.0)
        quantity_risk = min(quantity / 30000, 1.0)
        geo_risk = min(geo_distance / 1000, 1.0) if geo_distance > 300 else 0

        # Random noise for demo variety
        noise = random.uniform(0.01, 0.04)

        # Weighted hybrid score
        fraud_score = (
            0.30 * model_score +
            0.20 * expiry_risk +
            0.15 * split_risk +
            0.15 * transfer_risk +
            0.10 * quantity_risk +
            0.05 * geo_risk +
            0.05 * noise
        )

        fraud_score = min(max(fraud_score, 0), 1)

        # Risk level
        if fraud_score > 0.7:
            risk_level = "HIGH"
        elif fraud_score > 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Explainable reasons
        reasons = []
        if days_to_expiry < 30:
            reasons.append(f"Near-expiry batch ({int(days_to_expiry)} days remaining)")
        if split_count > 3:
            reasons.append(f"Excessive batch splits ({split_count} splits)")
        if transfer_frequency > 4:
            reasons.append(f"High transfer frequency ({transfer_frequency} transfers)")
        if quantity > 10000:
            reasons.append(f"Unusually large quantity ({quantity}g)")
        if geo_distance > 500:
            reasons.append(f"Cross-region transfer ({int(geo_distance)}km)")
        if batch_age_days > 365:
            reasons.append(f"Very old batch ({int(batch_age_days)} days)")

        return fraud_score, risk_level, reasons
