/* =========================================================
   ANNYADATA — CROP DOCTOR
   Camera / Upload / AI Analysis
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const cropSelect = document.getElementById("cropSelect");

    const cameraInput = document.getElementById("cameraInput");
    const fileInput = document.getElementById("fileInput");

    const previewImage = document.getElementById("previewImage");
    const previewPlaceholder = document.getElementById("previewPlaceholder");

    const analyzeButton = document.getElementById("analyzeButton");

    const cropResult = document.getElementById("cropResult");
    const prediction = document.getElementById("prediction");
    const confidence = document.getElementById("confidence");

    const predictionList = document.getElementById("predictionList");

    const verificationNotice =
        document.getElementById("verificationNotice");

    const anotherPhotoButton =
        document.getElementById("anotherPhotoButton");

    const askSamarthButton =
        document.getElementById("askSamarthButton");


    /* =====================================================
       CONFIGURATION
       ===================================================== */

    const BACKEND_URL = "https://api.samarth.business";

    let selectedFile = null;


    /* =====================================================
       ENABLE / DISABLE ANALYZE BUTTON
       ===================================================== */

    function updateAnalyzeButton() {

        const cropSelected = cropSelect.value !== "";
        const imageSelected = selectedFile !== null;

        analyzeButton.disabled =
            !(cropSelected && imageSelected);
    }


    cropSelect.addEventListener("change", () => {

        updateAnalyzeButton();

        /*
         * Hide an old result if the farmer changes the crop.
         * This prevents an old diagnosis from being confused
         * with the newly selected crop.
         */
        cropResult.style.display = "none";
    });


    /* =====================================================
       HANDLE IMAGE SELECTION
       ===================================================== */

    function handleImage(file) {

        if (!file) {
            return;
        }


        /* Make sure the selected file is an image */
        if (!file.type.startsWith("image/")) {

            alert("Please select an image file.");

            return;
        }


        selectedFile = file;


        /* Create preview */
        const imageURL = URL.createObjectURL(file);

        previewImage.src = imageURL;
        previewImage.style.display = "block";

        previewPlaceholder.style.display = "none";


        /* Hide previous result */
        cropResult.style.display = "none";


        /* Enable analyze button if crop is selected */
        updateAnalyzeButton();
    }


    /* Camera */
    cameraInput.addEventListener("change", (event) => {

        const file = event.target.files[0];

        handleImage(file);

    });


    /* Upload */
    fileInput.addEventListener("change", (event) => {

        const file = event.target.files[0];

        handleImage(file);

    });


    /* =====================================================
       ANALYZE CROP
       ===================================================== */

    analyzeButton.addEventListener("click", async () => {

        if (!selectedFile) {

            alert("Please take or upload a crop photo.");

            return;
        }


        if (!cropSelect.value) {

            alert("Please select the crop first.");

            return;
        }


        const crop = cropSelect.value;


        /* =================================================
           SPECIAL HANDLING FOR CURRENT MVP MODEL
           =================================================

           Rice/Paddy is the currently validated workflow.

           Other crops are kept visible in the UI but are
           not sent to the rice-focused model.
        */

        if (crop !== "rice") {

            alert(
                "The current Crop Doctor model is being validated for Rice / Paddy. " +
                "Support for additional crops will be added as Annyadata's own dataset grows."
            );

            return;
        }


        /* =================================================
           LOADING STATE
           ================================================= */

        const originalButtonText = analyzeButton.textContent;

        analyzeButton.disabled = true;
        analyzeButton.textContent = "Analyzing crop…";

        cropResult.style.display = "none";


        try {

            /* Build multipart form */
            const formData = new FormData();

            formData.append("image", selectedFile);
            formData.append("crop", crop);


            /* Call FastAPI backend */
            const response = await fetch(
                `${BACKEND_URL}/crop-doctor/analyze`,
                {
                    method: "POST",
                    body: formData
                }
            );


            /* Try to decode response */
            let data;

            try {

                data = await response.json();

            } catch (jsonError) {

                throw new Error(
                    "The Crop Doctor server returned an invalid response."
                );

            }


            /* API-level failure */
            if (!response.ok || data.success === false) {

                throw new Error(
                    data.error ||
                    `Crop Doctor request failed (${response.status}).`
                );

            }


            /* =================================================
               DISPLAY RESULT
               ================================================= */

            displayResult(data);


        } catch (error) {

            console.error(
                "Crop Doctor error:",
                error
            );


            alert(
                "We couldn't analyze this photo right now.\n\n" +
                error.message
            );


        } finally {

            analyzeButton.disabled = false;
            analyzeButton.textContent = originalButtonText;

            updateAnalyzeButton();

        }

    });


    /* =====================================================
       DISPLAY AI RESULT
       ===================================================== */

    function displayResult(data) {

        const resultPrediction =
            data.prediction || "Unknown";

        const resultConfidence =
            Number(data.confidence || 0);


        /* Main diagnosis */
        prediction.textContent =
            formatLabel(resultPrediction);


        /* Confidence */
        confidence.textContent =
            formatConfidence(resultConfidence);


        /* =================================================
           TOP PREDICTIONS
           ================================================= */

        predictionList.innerHTML = "";


        if (
            Array.isArray(data.top_predictions) &&
            data.top_predictions.length > 0
        ) {

            data.top_predictions.forEach((item) => {

                const row =
                    document.createElement("div");

                row.className =
                    "prediction-row";


                const label =
                    document.createElement("span");

                label.textContent =
                    formatLabel(item.label);


                const score =
                    document.createElement("strong");

                score.textContent =
                    formatConfidence(item.confidence);


                row.appendChild(label);
                row.appendChild(score);

                predictionList.appendChild(row);

            });

        } else {

            predictionList.innerHTML =
                `<div class="prediction-row">
                    <span>No additional predictions available</span>
                </div>`;

        }


        /* =================================================
           VOLUNTEER VERIFICATION
           ================================================= */

        if (data.requires_volunteer_verification) {

            verificationNotice.style.display =
                "block";

        } else {

            verificationNotice.style.display =
                "none";

        }


        /* Show result */
        cropResult.style.display =
            "block";


        /* Scroll result into view */
        setTimeout(() => {

            cropResult.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }, 100);

    }


    /* =====================================================
       FORMAT MODEL LABEL
       ===================================================== */

    function formatLabel(label) {

        if (!label) {
            return "Unknown";
        }

        return String(label)
            .replace(/_/g, " ")
            .replace(/\b\w/g, (letter) =>
                letter.toUpperCase()
            );

    }


    /* =====================================================
       FORMAT CONFIDENCE
       ===================================================== */

    function formatConfidence(value) {

        let number = Number(value);

        if (!Number.isFinite(number)) {
            return "0.0%";
        }

        /*
         * Handle either decimal or percentage values:
         *
         * 0.95 -> 95%
         * 0.80 -> 80%
         * 95   -> 95%
         * 100  -> 100%
         */

        if (number <= 1) {
            number = number * 100;
        }

        /*
         * Prevent impossible percentages such as:
         * 10000%
         */

        number = Math.max(0, Math.min(100, number));

        return `${number.toFixed(1)}%`;
    }


    /* =====================================================
       ANALYZE ANOTHER PHOTO
       ===================================================== */

    anotherPhotoButton.addEventListener("click", () => {

        selectedFile = null;


        /* Reset preview */
        previewImage.src = "";
        previewImage.style.display = "none";

        previewPlaceholder.style.display =
            "flex";


        /* Reset result */
        cropResult.style.display =
            "none";


        /* Reset inputs */
        cameraInput.value = "";
        fileInput.value = "";


        /* Reset crop */
        cropSelect.value = "";


        /* Disable analyze */
        updateAnalyzeButton();


        /* Scroll back to photo area */
        document.querySelector(".photo-workspace")
            ?.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

    });


    /* =====================================================
       ASK SAMARTH
       ===================================================== */

    askSamarthButton.addEventListener("click", () => {

        /*
         * The main Samarth voice interface already exists
         * in app.js. We return the farmer to the Farmer
         * Portal where they can talk to Samarth.
         */

        window.location.href =
            "../samarthAI.html#home";

    });


    /* =====================================================
       INITIAL STATE
       ===================================================== */

    updateAnalyzeButton();

});