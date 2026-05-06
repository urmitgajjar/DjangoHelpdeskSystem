import logging
import os
import pickle
import warnings

from django.conf import settings
from sklearn.exceptions import InconsistentVersionWarning

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(
    settings.BASE_DIR,
    "myapp",
    "ml_models",
    "department_classifier.pkl",
)

_model = None
_model_load_attempted = False
_model_load_error = None


def _get_model():
    global _model, _model_load_attempted, _model_load_error
    if _model_load_attempted:
        return _model

    _model_load_attempted = True
    try:
        with open(MODEL_PATH, "rb") as f:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always", InconsistentVersionWarning)
                _model = pickle.load(f)
            if any(issubclass(w.category, InconsistentVersionWarning) for w in captured):
                logger.warning(
                    "Department model was trained with a different scikit-learn version. "
                    "Model loaded, but retraining is recommended."
                )
    except Exception as exc:
        _model_load_error = exc
        logger.warning("Department model load failed: %s", exc)
        _model = None
    return _model


def predict_department(title, description):

    text = f"{title} {description}".lower()

    department_keywords = {
        "HR": [
            "hr", "human resources", "employee", "employees", "staff", "recruitment",
            "recruiting", "hiring", "interview", "onboarding", "offboarding", "joining",
            "offer letter", "internship", "apprenticeship", "training", "policy",
            "leave", "vacation", "holiday", "holidays", "time off", "pto", "attendance",
            "benefits", "medical reimbursement", "engagement", "survey", "attrition",
            "exit interview", "promotion", "transfer", "termination", "competency",
        ],
        "Finance": [
            "finance", "invoice", "invoices", "billing", "payment", "payments",
            "vendor payment", "purchase order", "po ", "reimbursement", "expense",
            "expenses", "budget", "tax", "audit", "payroll", "salary", "asset",
            "depreciation", "capitalization", "accounting", "ledger", "refund payment",
            "cost", "financial", "fund", "funds",
        ],
        "IT Support": [
            "it", "technical", "system", "software", "hardware", "laptop", "desktop",
            "workstation", "server", "database", "network", "wifi", "wi-fi", "vpn",
            "login", "password", "mfa", "multi-factor", "authentication", "api",
            "token", "access", "printer", "print server", "email", "os", "patch",
            "vulnerability", "security scan", "backup", "restore", "device", "mobile",
            "application", "app error", "bug", "error 401", "unauthorized",
        ],
        "Customer Support": [
            "customer", "client", "buyer", "order", "purchase history", "delivery",
            "delivered", "product", "item", "warranty", "return", "refund request",
            "complaint", "compensation", "subscription", "gift card", "app not available",
            "region", "cancelled", "custom order", "store", "service not available",
            "incorrect information", "support agent",
        ],
        "Operations": [
            "operations", "warehouse", "inventory", "stock", "production", "production line",
            "downtime", "equipment", "machine", "machinery", "cold storage", "temperature",
            "alarm", "safety", "incident", "near miss", "facility", "facilities",
            "logistics", "shipment", "supply", "maintenance", "quality", "inspection",
            "root cause", "process", "workflow", "plant",
        ],
        "Manager": [
            "manager", "management", "approval", "leadership", "senior leadership",
            "goal", "goals", "target", "targets", "quarterly", "strategy", "decision",
            "review", "business case", "closure decision", "market", "department heads",
            "change management", "communication plan", "escalation", "resource planning",
        ],
    }

    scores = {
        department: sum(1 for keyword in keywords if keyword in text)
        for department, keywords in department_keywords.items()
    }
    best_department = max(scores, key=scores.get)
    if scores[best_department] > 0:
        return best_department

    model = _get_model()
    if model is None:
        raise RuntimeError(f"Department model unavailable: {_model_load_error}")

    prediction = model.predict([text])[0]

    return prediction
