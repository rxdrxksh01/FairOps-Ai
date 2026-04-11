from tools.overview import get_dataset_overview, set_dataframe, get_dataframe
from tools.approval_by_group import get_approval_by_group
from tools.feature_importance import get_feature_importance, train_and_set_model, get_model
from tools.counterfactual import run_counterfactual
from tools.correlation import get_correlation

ALL_TOOLS = [
    get_dataset_overview,
    get_approval_by_group,
    get_feature_importance,
    run_counterfactual,
    get_correlation,
]