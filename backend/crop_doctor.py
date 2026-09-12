import io
import torch

from PIL import Image
from transformers import CLIPProcessor, CLIPModel


# ============================================================
# ANNYADATA CROP DOCTOR
# Generic multi-crop disease detection engine
#
# The farmer/application supplies the crop.
# The AI then performs crop-specific visual diagnosis.
# ============================================================

MODEL_ID = "Keetawan/clip-vit-large-patch14-plant-disease-finetuned"

_model = None
_processor = None


# ============================================================
# SUPPORTED CROPS AND CONDITIONS
# ============================================================

CROP_CONFIG = {

    "rice": {
        "name": "Rice",
        "labels": [
            "Rice leaf with Bacterial blight",
            "Rice leaf with Blast",
            "Rice leaf with Brown spot",
            "Rice leaf with Tungro",
            "Healthy Rice leaf",
        ],
    },

    "tomato": {
        "name": "Tomato",
        "labels": [
            "Tomato leaf with Bacterial spot",
            "Tomato leaf with Early blight",
            "Tomato leaf with Late blight",
            "Tomato leaf with Leaf Mold",
            "Tomato leaf with Septoria leaf spot",
            "Tomato leaf with Spider mites (Two-spotted spider mite)",
            "Tomato leaf with Target Spot",
            "Tomato leaf with Tomato Yellow Leaf Curl Virus",
            "Tomato leaf with Tomato mosaic virus",
            "Healthy Tomato leaf",
        ],
    },

    "potato": {
        "name": "Potato",
        "labels": [
            "Potato leaf with Early blight",
            "Potato leaf with Late blight",
            "Healthy Potato leaf",
        ],
    },

    "corn": {
        "name": "Corn",
        "labels": [
            "Corn leaf with Cercospora leaf spot (Gray leaf spot)",
            "Corn leaf with Common rust",
            "Corn leaf with Northern Leaf Blight",
            "Healthy Corn leaf",
        ],
    },

    "apple": {
        "name": "Apple",
        "labels": [
            "Apple leaf with Apple scab",
            "Apple leaf with Black rot",
            "Apple leaf with Cedar apple rust",
            "Healthy Apple leaf",
        ],
    },

    "grape": {
        "name": "Grape",
        "labels": [
            "Grape leaf with Black rot",
            "Grape leaf with Esca (Black Measles)",
            "Grape leaf with Leaf blight (Isariopsis Leaf Spot)",
            "Healthy Grape leaf",
        ],
    },

    "pepper": {
        "name": "Pepper",
        "labels": [
            "Pepper bell leaf with Bacterial spot",
            "Healthy Pepper bell leaf",
        ],
    },

    "strawberry": {
        "name": "Strawberry",
        "labels": [
            "Strawberry leaf with Leaf scorch",
            "Healthy Strawberry leaf",
        ],
    },

    "soybean": {
        "name": "Soybean",
        "labels": [
            "Healthy Soybean leaf",
        ],
    },

    "durian": {
        "name": "Durian",
        "labels": [
            "Durian leaf with Algal Leaf Spot",
            "Durian leaf with Leaf Blight",
            "Durian leaf with Leaf Spot",
            "Healthy Durian leaf",
        ],
    },

    "oil_palm": {
        "name": "Oil Palm",
        "labels": [
            "Oil Palm leaf with brown spots",
            "Healthy Oil Palm leaf",
            "Oil Palm leaf with white scale",
        ],
    },

    "orange": {
        "name": "Orange",
        "labels": [
            "Orange leaf with Huanglongbing (Citrus greening)",
        ],
    },
}


# ============================================================
# MODEL LOADING
# ============================================================

def load_model():

    global _model
    global _processor

    if _model is None or _processor is None:

        print("Loading Annyadata Crop Doctor model...")

        _model = CLIPModel.from_pretrained(MODEL_ID)

        _processor = CLIPProcessor.from_pretrained(
            MODEL_ID
        )

        _model.eval()

        print("Crop Doctor model loaded successfully.")

    return _model, _processor


# ============================================================
# GET SUPPORTED CROPS
# ============================================================

def get_supported_crops():

    return [
        {
            "id": crop_id,
            "name": config["name"],
            "conditions": config["labels"],
        }
        for crop_id, config in CROP_CONFIG.items()
    ]


# ============================================================
# DIAGNOSE CROP
# ============================================================

def diagnose_crop(
    image_bytes: bytes,
    crop: str,
):

    crop = crop.lower().strip()

    # --------------------------------------------------------
    # Validate crop
    # --------------------------------------------------------

    if crop not in CROP_CONFIG:

        return {
            "success": False,
            "error": "Unsupported crop",
            "supported_crops": list(
                CROP_CONFIG.keys()
            ),
        }


    model, processor = load_model()

    config = CROP_CONFIG[crop]

    labels = config["labels"]


    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    try:

        image = Image.open(
            io.BytesIO(image_bytes)
        ).convert("RGB")

    except Exception:

        return {
            "success": False,
            "error": "Invalid image file",
        }


    # --------------------------------------------------------
    # CLIP inference
    # --------------------------------------------------------

    inputs = processor(
        text=labels,
        images=image,
        return_tensors="pt",
        padding=True,
    )

    with torch.no_grad():

        outputs = model(**inputs)

        probabilities = (
            outputs.logits_per_image
            .softmax(dim=1)[0]
        )


    # --------------------------------------------------------
    # Top predictions
    # --------------------------------------------------------

    top_k = min(
        5,
        len(labels)
    )

    values, indices = torch.topk(
        probabilities,
        k=top_k,
    )

    top_predictions = []

    for value, index in zip(
        values,
        indices
    ):

        label = labels[
            index.item()
        ]

        confidence = float(
            value.item() * 100
        )

        top_predictions.append({
            "label": label,
            "confidence": round(
                confidence,
                2
            ),
        })


    # --------------------------------------------------------
    # Best prediction
    # --------------------------------------------------------

    best_index = indices[0].item()

    prediction = labels[
        best_index
    ]

    confidence = float(
        values[0].item() * 100
    )


    # --------------------------------------------------------
    # Determine healthy / disease
    # --------------------------------------------------------

    is_healthy = (
        "healthy"
        in prediction.lower()
    )


    # --------------------------------------------------------
    # Volunteer verification
    #
    # We use a conservative threshold for real-world
    # farmer photographs.
    # --------------------------------------------------------

    requires_verification = (
        confidence < 75
    )


    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {

        "success": True,

        "crop": crop,

        "crop_name": config[
            "name"
        ],

        "prediction": prediction,

        "confidence": round(
            confidence,
            2
        ),

        "is_healthy": is_healthy,

        "requires_volunteer_verification":
            requires_verification,

        "top_predictions":
            top_predictions,
    }


# ============================================================
# GENERIC ENTRY POINT
# ============================================================

def analyze_crop(
    image_bytes: bytes,
    crop: str,
):

    """
    Main Crop Doctor entry point.

    Example:

        result = analyze_crop(
            image_bytes,
            "rice"
        )
    """

    return diagnose_crop(
        image_bytes,
        crop
    )