from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'json', 'xlsx', 'xls', 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@dataclass
class CriteriaResult:
    """Data class to hold a single criterion result."""
    criteria_name: str
    features_mapped: str
    feature_results: str
    formula: str
    result: Union[bool, str, int, float]


class CriteriaGenerator:
    """Comprehensive criteria generator for video feature analysis."""

    def __init__(self, wat_threshold: float = 2.0):
        self.wat_threshold = wat_threshold
        self.data = {}
        self.processed_data = {}

    def load_data(self, data_dict: dict) -> bool:
        """Load data from dictionary."""
        try:
            self.data = data_dict
            self._preprocess_data()
            return True
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False

    def _preprocess_data(self) -> None:
        """Pre-process raw data: convert types, handle empty values."""
        self.processed_data = {}
        
        for key, value in self.data.items():
            if value == "" or value is None:
                self.processed_data[key] = None
            elif isinstance(value, bool):
                self.processed_data[key] = value
            elif isinstance(value, (int, float)):
                self.processed_data[key] = value
            elif isinstance(value, str):
                if value.upper() == "TRUE":
                    self.processed_data[key] = True
                elif value.upper() == "FALSE":
                    self.processed_data[key] = False
                elif re.match(r'^\d{2}:\d{2}:\d{2}$', value):
                    parts = value.split(':')
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    self.processed_data[key] = seconds
                else:
                    self.processed_data[key] = value
            else:
                self.processed_data[key] = value

    def _get(self, key: str, default: Any = None) -> Any:
        """Safely get a value from processed data."""
        return self.processed_data.get(key, default)

    def _exists(self, key: str) -> bool:
        """Check if a key exists and has a non-None value."""
        return key in self.processed_data and self.processed_data[key] is not None

    def _is_true(self, key: str) -> bool:
        """Check if a value is explicitly True."""
        return self._get(key) is True

    def _min_timestamp(self, *keys: str) -> Optional[float]:
        """Get the minimum timestamp from available keys."""
        timestamps = [self._get(key) for key in keys if self._exists(key) and isinstance(self._get(key), (int, float))]
        return min(timestamps) if timestamps else None

    def _normalize_aspect_ratio(self, width: Optional[float], height: Optional[float]) -> str:
        """Normalize aspect ratio to common formats."""
        if width and height and height != 0:
            ratio = width / height
            if abs(ratio - (16/9)) < 0.01:
                return "16:9"
            elif abs(ratio - 1.0) < 0.01:
                return "1:1"
            elif abs(ratio - (9/16)) < 0.01:
                return "9:16"
            elif abs(ratio - (4/5)) < 0.01:
                return "4:5"
        return "Unknown"

    def _contains_keyword(self, text: Optional[str], keywords: List[str]) -> bool:
        """Check if text contains any keywords (case-insensitive)."""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _calculate_text_overlap(self, text1: Optional[str], text2: Optional[str]) -> float:
        """Calculate word overlap ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        
        text1_normalized = re.sub(r'[^\w\s]', '', text1.lower()).split()
        text2_normalized = re.sub(r'[^\w\s]', '', text2.lower()).split()
        
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are', 'was', 'were'}
        text1_words = set(w for w in text1_normalized if w not in stop_words)
        text2_words = set(w for w in text2_normalized if w not in stop_words)
        
        if not text1_words:
            return 0.0
        
        shared_words = text1_words.intersection(text2_words)
        return len(shared_words) / len(text1_words)

    def _criteria_early_benefit_shown(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._exists('product_placement_visually_introduced_time') and self._exists('product_benefits_time_first_mentioned'):
            intro_time = self._get('product_placement_visually_introduced_time')
            benefit_time = self._get('product_benefits_time_first_mentioned')
            if intro_time <= self.wat_threshold and abs(benefit_time - intro_time) <= 2:
                return (
                    "product_placement_visually_introduced_time, product_benefits_time_first_mentioned",
                    f"{intro_time}s, {benefit_time}s",
                    "product_placement_visually_introduced_time <= WAT AND ABS(difference) <= 2s",
                    True
                )
        return ("N/A", "N/A", "N/A", False)

    def _criteria_parents_presence(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('parents_present'):
            return ("parents_present", "True", "parents_present = True", True)
        return ("parents_present", "False", "parents_present = False", False)

    def _criteria_editing_tightness(self) -> Tuple[str, str, str, Union[bool, str]]:
        score = 0
        breakdown = []
        
        if self._is_true('editing_and_visual_effects'):
            score += 20
            breakdown.append("editing_and_visual_effects: +20")
        
        pace = self._get('visual_pace', "").lower()
        if pace == "fast":
            score += 40
            breakdown.append("visual_pace=Fast: +40")
        elif pace == "medium":
            score += 20
            breakdown.append("visual_pace=Medium: +20")
        
        cuts = self._get('number_of_editing_cuts_or_visual_transitions', 0)
        if cuts < 2:
            breakdown.append(f"cuts < 2: +0")
        elif 2 <= cuts <= 4:
            score += 15
            breakdown.append(f"2-4 cuts: +15")
        elif 5 <= cuts <= 6:
            score += 30
            breakdown.append(f"5-6 cuts: +30")
        else:
            score += 40
            breakdown.append(f"7+ cuts: +40")
        
        breakdown_str = ", ".join(breakdown)
        return (
            "editing_and_visual_effects, visual_pace, number_of_editing_cuts_or_visual_transitions",
            breakdown_str,
            "Score-based formula (20, 20-40, 0-40)",
            score
        )

    def get_creative_brand_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria_methods = [
            ("Early Benefit Shown", self._criteria_early_benefit_shown),
            ("Parents Presence", self._criteria_parents_presence),
            ("Editing Tightness", self._criteria_editing_tightness),
        ]
        
        for criteria_name, method in criteria_methods:
            features, feature_results, formula, result = method()
            results.append(CriteriaResult(
                criteria_name=criteria_name,
                features_mapped=features,
                feature_results=feature_results,
                formula=formula,
                result=result
            ))
        
        return results

    def _meta_file_type_check(self) -> Tuple[str, str, str, Union[bool, str]]:
        file_type = self._get('file_type', '').upper()
        result = file_type in ['MP4', 'MOV', 'GIF']
        return ("file_type", f"'{self._get('file_type')}'", "if file_type in ['MP4', 'MOV', 'GIF']", result)

    def _meta_ratio_facebook_feed(self) -> Tuple[str, str, str, Union[bool, str]]:
        aspect_ratio = self._get('aspect_ratio', 0)
        rounded = round(aspect_ratio, 2)
        normalized = self._normalize_aspect_ratio(self._get('video_width'), self._get('video_height'))
        result = rounded == 1.00 or rounded == 0.80
        return ("aspect_ratio", f"{aspect_ratio} -> '{normalized}'", f"ROUND(aspect_ratio, 2) == 1.00 OR 0.80", result)

    def _meta_sound_recommended(self) -> Tuple[str, str, str, Union[bool, str]]:
        has_music = self._is_true('music')
        has_dialogue = self._is_true('dialogue')
        voiceover = self._get('voiceover_or_direct_dialogue', "")
        result = has_music or has_dialogue or voiceover != ""
        features_str = f"music: {has_music}, dialogue: {has_dialogue}, voiceover: '{voiceover}'"
        return ("music, dialogue, voiceover_or_direct_dialogue", features_str, "music OR dialogue OR voiceover", result)

    def get_facebook_feed_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria = [
            ("File Type MP4/MOV/GIF", self._meta_file_type_check),
            ("Ratio 1:1 or 4:5", self._meta_ratio_facebook_feed),
            ("Sound Recommended", self._meta_sound_recommended),
        ]
        
        for name, method in criteria:
            features, feature_results, formula, result = method()
            results.append(CriteriaResult(
                criteria_name=name,
                features_mapped=features,
                feature_results=feature_results,
                formula=formula,
                result=result
            ))
        
        return results

    def get_all_results(self) -> Dict[str, List[CriteriaResult]]:
        """Get all results as a dictionary."""
        return {
            "Creative & Brand Criteria": self.get_creative_brand_criteria(),
            "META: Facebook Feed": self.get_facebook_feed_criteria(),
        }


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Use JSON, CSV, or Excel files."}), 400
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        try:
            if file_ext == 'json':
                data = json.load(file)
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
            elif file_ext == 'csv':
                df = pd.read_csv(file)
                data = df.iloc[0].to_dict()
            elif file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file)
                data = df.iloc[0].to_dict()
            else:
                return jsonify({"error": "Unsupported file format"}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400
        
        wat_threshold = request.form.get('wat_threshold', 2.0, type=float)
        
        generator = CriteriaGenerator(wat_threshold=wat_threshold)
        if not generator.load_data(data):
            return jsonify({"error": "Failed to process data"}), 500
        
        results = generator.get_all_results()
        
        serialized_results = {}
        for category, criteria_list in results.items():
            serialized_results[category] = [
                {
                    "criteria_name": c.criteria_name,
                    "features_mapped": c.features_mapped,
                    "feature_results": str(c.feature_results),
                    "formula": c.formula,
                    "result": str(c.result),
                }
                for c in criteria_list
            ]
        
        return jsonify({
            "success": True,
            "filename": file.filename,
            "data": data,
            "results": serialized_results
        })
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
