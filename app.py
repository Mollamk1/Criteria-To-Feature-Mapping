from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

app = Flask(__name__)
CORS(app)


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
                    # Time format: HH:MM:SS → seconds
                    parts = value.split(':')
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    self.processed_data[key] = seconds
                else:
                    # Try to convert to number if possible
                    try:
                        if '.' in value:
                            self.processed_data[key] = float(value)
                        else:
                            self.processed_data[key] = int(value)
                    except (ValueError, TypeError):
                        # Not a number, keep as string
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

    # ========== CREATIVE & BRAND CRITERIA ==========
    
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

    def _criteria_first_mention_brand_logo(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('brand_logo') or (self._exists('brand_logo_name') and self._get('brand_logo_name') != ""):
            return (
                "brand_logo, brand_logo_name",
                "True",
                "Brand logo present",
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
            breakdown.append("editing: +20")
        
        pace = self._get('visual_pace', "").lower()
        if pace == "fast":
            score += 40
            breakdown.append("fast pace: +40")
        elif pace == "medium":
            score += 20
            breakdown.append("medium pace: +20")
        
        cuts = self._get('number_of_editing_cuts_or_visual_transitions', 0)
        if cuts < 2:
            score += 0
        elif 2 <= cuts <= 4:
            score += 15
            breakdown.append("2-4 cuts: +15")
        elif 5 <= cuts <= 6:
            score += 30
            breakdown.append("5-6 cuts: +30")
        else:
            score += 40
            breakdown.append("7+ cuts: +40")
        
        breakdown_str = ", ".join(breakdown) if breakdown else "No score"
        return (
            "editing_and_visual_effects, visual_pace, number_of_editing_cuts_or_visual_transitions",
            breakdown_str,
            "Score: 0-100",
            score
        )

    def _criteria_humor_playful_tone(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('humor'):
            return ("humor", "True", "humor = True", "Humorous")
        
        tone = self._get('tone_of_voice', "")
        appeal = self._get('emotional_appeal', "")
        
        if self._contains_keyword(tone, ["playful", "fun", "joyful", "energetic"]):
            return ("tone_of_voice, emotional_appeal", f"{tone}", "Contains playful keywords", "Playful")
        
        if self._contains_keyword(tone, ["calm", "informative", "neutral"]):
            return ("tone_of_voice", tone, "Contains calm keywords", "Neutral")
        
        if self._contains_keyword(appeal, ["safety", "reassurance"]):
            return ("emotional_appeal", appeal, "Contains reassurance keywords", "Serious")
        
        return ("tone_of_voice, emotional_appeal", f"{tone}, {appeal}", "No specific tone", "Ambiguous")

    def _criteria_music_present(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('music'):
            return ("music", "True", "music = True", True)
        return ("music", "False", "music = False", False)

    def _criteria_dialogue_present(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('dialogue'):
            return ("dialogue", "True", "dialogue = True", True)
        return ("dialogue", "False", "dialogue = False", False)

    def get_creative_brand_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria_methods = [
            ("Early Benefit Shown", self._criteria_early_benefit_shown),
            ("Brand Logo Present", self._criteria_first_mention_brand_logo),
            ("Parents Presence", self._criteria_parents_presence),
            ("Editing Tightness", self._criteria_editing_tightness),
            ("Humor/Playful Tone", self._criteria_humor_playful_tone),
            ("Music Present", self._criteria_music_present),
            ("Dialogue Present", self._criteria_dialogue_present),
        ]
        
        for criteria_name, method in criteria_methods:
            try:
                features, feature_results, formula, result = method()
                results.append(CriteriaResult(
                    criteria_name=criteria_name,
                    features_mapped=features,
                    feature_results=feature_results,
                    formula=formula,
                    result=result
                ))
            except Exception as e:
                print(f"Error in {criteria_name}: {str(e)}")
        
        return results

    # ========== META CRITERIA ==========
    
    def _meta_file_type_check(self) -> Tuple[str, str, str, Union[bool, str]]:
        file_type = self._get('file_type', '').upper()
        result = file_type in ['MP4', 'MOV', 'GIF']
        return ("file_type", f"'{self._get('file_type')}'", "MP4, MOV, or GIF", result)

    def _meta_ratio_facebook_feed(self) -> Tuple[str, str, str, Union[bool, str]]:
        aspect_ratio = self._get('aspect_ratio', 0)
        rounded = round(aspect_ratio, 2)
        result = rounded == 1.00 or rounded == 0.80
        return ("aspect_ratio", f"{aspect_ratio}", "1:1 (1.00) or 4:5 (0.80)", result)

    def _meta_sound_recommended(self) -> Tuple[str, str, str, Union[bool, str]]:
        has_music = self._is_true('music')
        has_dialogue = self._is_true('dialogue')
        result = has_music or has_dialogue
        return ("music, dialogue", f"Music: {has_music}, Dialogue: {has_dialogue}", "Has music OR dialogue", result)

    def _meta_safe_zone_top(self) -> Tuple[str, str, str, Union[bool, str]]:
        safe_top = self._get('safe_zone_size_top', 0)
        result = safe_top >= 14
        return ("safe_zone_size_top", f"{safe_top}px", ">= 14px", result)

    def _meta_duration_valid(self) -> Tuple[str, str, str, Union[bool, str]]:
        duration = self._get('video_duration', 0)
        result = 1 <= duration <= 120
        return ("video_duration", f"{duration}s", "1s to 120s", result)

    def _meta_resolution_check(self) -> Tuple[str, str, str, Union[bool, str]]:
        width = self._get('video_width', 0)
        height = self._get('video_height', 0)
        result = width >= 720 and height >= 720
        return ("video_width, video_height", f"{width}x{height}", ">= 720x720", result)

    def get_facebook_feed_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria = [
            ("File Type", self._meta_file_type_check),
            ("Aspect Ratio (1:1 or 4:5)", self._meta_ratio_facebook_feed),
            ("Sound Recommended", self._meta_sound_recommended),
            ("Safe Zone Top", self._meta_safe_zone_top),
            ("Duration Valid", self._meta_duration_valid),
            ("Resolution Check", self._meta_resolution_check),
        ]
        
        for name, method in criteria:
            try:
                features, feature_results, formula, result = method()
                results.append(CriteriaResult(
                    criteria_name=name,
                    features_mapped=features,
                    feature_results=feature_results,
                    formula=formula,
                    result=result
                ))
            except Exception as e:
                print(f"Error in {name}: {str(e)}")
        
        return results

    def _tiktok_aspect_ratio(self) -> Tuple[str, str, str, Union[bool, str]]:
        aspect_ratio = self._get('aspect_ratio', 0)
        rounded = round(aspect_ratio, 2)
        result = rounded == 0.56
        return ("aspect_ratio", f"{aspect_ratio}", "9:16 (0.56)", result)

    def _tiktok_resolution(self) -> Tuple[str, str, str, Union[bool, str]]:
        width = self._get('video_width', 0)
        height = self._get('video_height', 0)
        result = width >= 540 and height >= 960
        return ("video_width, video_height", f"{width}x{height}", ">= 540x960", result)

    def _tiktok_duration(self) -> Tuple[str, str, str, Union[bool, str]]:
        duration = self._get('video_duration', 0)
        result = 5 <= duration <= 60
        return ("video_duration", f"{duration}s", "5s to 60s", result)

    def _tiktok_sound(self) -> Tuple[str, str, str, Union[bool, str]]:
        has_music = self._is_true('music')
        has_dialogue = self._is_true('dialogue')
        result = has_music or has_dialogue
        return ("music, dialogue", f"Music: {has_music}, Dialogue: {has_dialogue}", "Has audio", result)

    def get_tiktok_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria = [
            ("Aspect Ratio (9:16)", self._tiktok_aspect_ratio),
            ("Resolution (540x960)", self._tiktok_resolution),
            ("Duration (5-60s)", self._tiktok_duration),
            ("Sound Required", self._tiktok_sound),
        ]
        
        for name, method in criteria:
            try:
                features, feature_results, formula, result = method()
                results.append(CriteriaResult(
                    criteria_name=name,
                    features_mapped=features,
                    feature_results=feature_results,
                    formula=formula,
                    result=result
                ))
            except Exception as e:
                print(f"Error in {name}: {str(e)}")
        
        return results

    def get_all_results(self) -> Dict[str, List[CriteriaResult]]:
        """Get all results as a dictionary."""
        return {
            "Creative & Brand Criteria": self.get_creative_brand_criteria(),
            "META: Facebook Feed": self.get_facebook_feed_criteria(),
            "TikTok Guidelines": self.get_tiktok_criteria(),
        }


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    print("\n" + "="*60)
    print("PROCESSING REQUEST")
    print("="*60)
    
    try:
        # Check if file exists
        if 'file' not in request.files:
            print("ERROR: No file in request")
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        print(f"✓ File: {file.filename}")
        
        # Parse JSON
        try:
            data = json.load(file)
            print(f"✓ JSON parsed successfully")
        except Exception as e:
            print(f"ERROR: Failed to parse JSON: {str(e)}")
            return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
        
        # Get WAT threshold
        wat_threshold = request.form.get('wat_threshold', 2.0, type=float)
        print(f"✓ WAT Threshold: {wat_threshold}")
        
        # Generate results
        print(f"→ Generating criteria...")
        generator = CriteriaGenerator(wat_threshold=wat_threshold)
        
        if not generator.load_data(data):
            print("ERROR: Failed to load data")
            return jsonify({"error": "Failed to process data"}), 500
        
        results = generator.get_all_results()
        print(f"✓ Generated {len(results)} result categories")
        
        # Serialize results
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
        
        print(f"✓ Results serialized")
        print("="*60)
        print("✓ SUCCESS!")
        print("="*60 + "\n")
        
        return jsonify({
            "success": True,
            "filename": file.filename,
            "results": serialized_results
        })
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("="*60 + "\n")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "OK"})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("CRITERIA GENERATOR STARTING")
    print("="*60)
    print("✓ Server running on http://0.0.0.0:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
