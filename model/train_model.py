"""
Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
Module: Random Forest Machine Learning Model Training

This script:
1. Generates a realistic synthetic SME cross-border payment risk dataset.
2. Uses train_test_split with fixed random_state=42 for reproducibility.
3. Trains a RandomForestClassifier to predict LOW, MEDIUM, or HIGH risk.
4. Evaluates Accuracy, Precision, Recall, and F1 Score.
5. Saves the trained model to model/random_forest_model.pkl, dataset to model/dataset.csv,
   and metrics to model/metrics.json.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import joblib

def generate_sme_dataset(n_samples=6000, random_state=42):
    np.random.seed(random_state)
    
    # 3 classes: 0 = LOW RISK, 1 = MEDIUM RISK, 2 = HIGH RISK
    # Distribution: ~58% Low Risk, ~25% Medium Risk, ~17% High Risk
    n_low = int(n_samples * 0.58)
    n_med = int(n_samples * 0.25)
    n_high = n_samples - n_low - n_med
    
    # === 1. LOW RISK (Legitimate established SME trade transactions) ===
    low_amounts = np.random.uniform(500, 14000, n_low)
    low_freq = np.random.randint(1, 5, n_low)
    low_prev_tx = np.random.randint(15, 120, n_low)
    low_suspicious = np.zeros(n_low, dtype=int)
    low_account_age = np.random.randint(12, 60, n_low)
    low_corridor_risk = np.random.uniform(0.1, 0.35, n_low)
    low_labels = np.zeros(n_low, dtype=int)
    
    # === 2. MEDIUM RISK (Moderate variance, newer accounts or unusual volume) ===
    med_amounts = np.random.uniform(15000, 48000, n_med)
    med_freq = np.random.randint(5, 10, n_med)
    med_prev_tx = np.random.randint(3, 20, n_med)
    med_suspicious = np.random.choice([0, 1, 2], size=n_med, p=[0.3, 0.5, 0.2])
    med_account_age = np.random.randint(3, 18, n_med)
    med_corridor_risk = np.random.uniform(0.35, 0.70, n_med)
    med_labels = np.ones(n_med, dtype=int)
    
    # === 3. HIGH RISK (Anomalously large amounts, spike frequency, suspicious flags) ===
    high_amounts = np.random.uniform(55000, 300000, n_high)
    high_freq = np.random.randint(9, 25, n_high)
    high_prev_tx = np.random.randint(0, 8, n_high)
    high_suspicious = np.random.randint(2, 7, n_high)
    high_account_age = np.random.randint(1, 7, n_high)
    high_corridor_risk = np.random.uniform(0.65, 0.95, n_high)
    high_labels = np.full(n_high, 2, dtype=int)
    
    # Concatenate all categories
    amounts = np.concatenate([low_amounts, med_amounts, high_amounts])
    frequencies = np.concatenate([low_freq, med_freq, high_freq])
    prev_txs = np.concatenate([low_prev_tx, med_prev_tx, high_prev_tx])
    suspicious = np.concatenate([low_suspicious, med_suspicious, high_suspicious])
    account_ages = np.concatenate([low_account_age, med_account_age, high_account_age])
    corridor_risks = np.concatenate([low_corridor_risk, med_corridor_risk, high_corridor_risk])
    labels = np.concatenate([low_labels, med_labels, high_labels])
    
    # Introduce 1.5% realistic real-world border noise for authentic academic evaluation
    noise_indices = np.random.choice(n_samples, size=int(n_samples * 0.015), replace=False)
    for idx in noise_indices:
        if labels[idx] == 0:
            labels[idx] = 1
        elif labels[idx] == 1:
            labels[idx] = np.random.choice([0, 2])
        elif labels[idx] == 2:
            labels[idx] = 1

    # Feature engineering: Amount-to-Age Ratio
    amount_to_age = amounts / (account_ages + 0.5)

    # Compile DataFrame
    df = pd.DataFrame({
        'amount': np.round(amounts, 2),
        'frequency': frequencies,
        'previous_transactions': prev_txs,
        'suspicious_transactions': suspicious,
        'account_age': account_ages,
        'corridor_risk': np.round(corridor_risks, 3),
        'amount_to_age_ratio': np.round(amount_to_age, 2),
        'risk_label': labels
    })
    
    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return df

def train_and_evaluate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base_dir, exist_ok=True)
    
    print("==================================================================")
    print("  RISK-ADAPTIVE SMART CONTRACT SETTLEMENT FOR SME PAYMENTS        ")
    print("  Machine Learning Module: Random Forest Classifier Training       ")
    print("==================================================================")
    
    # 1. Generate Dataset
    print("[1/5] Generating SME Cross-Border Payments Risk Dataset...")
    df = generate_sme_dataset(n_samples=6000, random_state=42)
    dataset_path = os.path.join(base_dir, "dataset.csv")
    df.to_csv(dataset_path, index=False)
    print(f"      Saved dataset ({len(df)} samples) to: {dataset_path}")
    print(f"      Class distribution:\n{df['risk_label'].value_counts().to_dict()}")
    
    # 2. Features and Target Split
    feature_cols = [
        'amount', 
        'frequency', 
        'previous_transactions', 
        'suspicious_transactions', 
        'account_age', 
        'corridor_risk', 
        'amount_to_age_ratio'
    ]
    X = df[feature_cols]
    y = df['risk_label']
    
    # 3. Train Test Split
    print("[2/5] Splitting data (75% Train, 25% Test) with random_state=42...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    print(f"      Train samples: {len(X_train)} | Test samples: {len(X_test)}")
    
    # 4. Model Training
    print("[3/5] Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    print("      Model training complete!")
    
    # 5. Model Evaluation
    print("[4/5] Evaluating Model Performance on Test Set...")
    y_pred = rf_model.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted')
    rec = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"      Accuracy:  {acc * 100:.2f}%")
    print(f"      Precision: {prec * 100:.2f}%")
    print(f"      Recall:    {rec * 100:.2f}%")
    print(f"      F1 Score:  {f1 * 100:.2f}%")
    
    report = classification_report(y_test, y_pred, target_names=['LOW RISK', 'MEDIUM RISK', 'HIGH RISK'])
    print("\nClassification Report:\n" + report)
    
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    # Feature Importances
    importances = dict(zip(feature_cols, [round(float(x), 4) for x in rf_model.feature_importances_]))
    print(f"      Feature Importances: {importances}")
    
    # 6. Save Model and Metrics
    print("[5/5] Saving model artifacts...")
    model_path = os.path.join(base_dir, "random_forest_model.pkl")
    joblib.dump({
        'model': rf_model,
        'feature_names': feature_cols,
        'classes': ['LOW', 'MEDIUM', 'HIGH'],
        'random_state': 42
    }, model_path)
    print(f"      Model saved to: {model_path}")
    
    metrics = {
        'model_name': 'Random Forest Classifier',
        'n_estimators': 100,
        'random_state': 42,
        'accuracy': round(acc * 100, 2),
        'precision': round(prec * 100, 2),
        'recall': round(rec * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'total_samples': len(df),
        'test_samples': len(X_test),
        'feature_importances': importances,
        'confusion_matrix': cm
    }
    
    metrics_path = os.path.join(base_dir, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"      Evaluation metrics saved to: {metrics_path}")
    print("==================================================================")
    print("  Random Forest Model Pipeline successfully completed!           ")
    print("==================================================================")

if __name__ == '__main__':
    train_and_evaluate()
