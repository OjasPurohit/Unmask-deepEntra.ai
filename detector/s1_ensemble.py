from PIL import Image

from models.model_a import predict_model_a
from models.model_b import predict_model_b
from models.model_c import predict_model_c


def predict_s1(image):
    """
    Run the three deep-learning models and combine their scores.

    Returns:
        dict containing:
        - score: combined S1 fake probability
        - model_a: Model A score
        - model_b: Model B score
        - model_c: Model C score
    """

    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL Image")

    image = image.convert("RGB")

    # Run all three models
    score_a = predict_model_a(image)
    score_b = predict_model_b(image)
    score_c = predict_model_c(image)

    # Temporary equal-weight ensemble.
    # These weights are engineering defaults, not scientifically
    # optimized weights. They can be calibrated later using the
    # evaluation dataset.
    s1_score = (
        score_a * 0.3333
        + score_b * 0.3333
        + score_c * 0.3334
    )

    return {
        "score": s1_score,
        "model_a": score_a,
        "model_b": score_b,
        "model_c": score_c,
    }