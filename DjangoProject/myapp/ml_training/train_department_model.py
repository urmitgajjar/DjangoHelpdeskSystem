import pandas as pd
import pickle
from pathlib import Path

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    log_loss
)

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "helpdesk_tickets_cleaned.csv"
MODEL_PATH = ROOT.parent / "ml_models" / "department_classifier.pkl"

df = pd.read_csv(DATASET_PATH)

df["title"] = df["title"].fillna("")
df["description"] = df["description"].fillna("")
df["department"] = df["department"].fillna("")

df["text"] = df["title"] + " " + df["description"]

X = df["text"]
y = df["department"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=7,
    stratify=y
)

model = Pipeline([
    ("tfidf", TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=10000
    )),
    ("clf", LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    ))
])

model.fit(X_train, y_train)

preds = model.predict(X_test)
probs = model.predict_proba(X_test)

accuracy = accuracy_score(y_test, preds)
precision = precision_score(y_test, preds, average="weighted")
recall = recall_score(y_test, preds, average="weighted")
f1 = f1_score(y_test, preds, average="weighted")
loss = log_loss(y_test, probs)

cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")

print("\n========== MODEL EVALUATION RESULTS ==========\n")

print(f"Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Precision: {precision:.4f} ({precision * 100:.2f}%)")
print(f"Recall: {recall:.4f} ({recall * 100:.2f}%)")
print(f"F1 Score: {f1:.4f} ({f1 * 100:.2f}%)")
print(f"Log Loss: {loss:.4f}")

print("\nCross Validation Scores:")
print(cv_scores)

print(f"\nAverage Cross Validation Accuracy: {cv_scores.mean():.4f} ({cv_scores.mean() * 100:.2f}%)")

print("\nClassification Report:\n")
print(classification_report(y_test, preds))

print("\nConfusion Matrix:\n")
print(confusion_matrix(y_test, preds))

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print("\nModel saved successfully")
print(f"Saved at: {MODEL_PATH}")