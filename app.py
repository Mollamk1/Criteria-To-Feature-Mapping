from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
import re
import traceback
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
            traceback.print_exc()
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
        if self._is_true('brand_logo') or (self._exists('brand_logo_name') and self._get('brand_logo_name') != "") or self._is_true('brand_mentioned_in_audio'):
            min_time = self._min_timestamp('brand_logo_introduced_time', 'brand_audio_introduced_time')
            if min_time is not None:
                return (
                    "brand_logo, brand_logo_name, brand_mentioned_in_audio, brand_logo_introduced_time, brand_audio_introduced_time",
                    f"{min_time}s",
                    "MIN(available timestamps)",
                    min_time
                )
        return ("N/A", "N/A", "N/A", "N/A")

    def _criteria_number_mentions_brand_logo(self) -> Tuple[str, str, str, Union[bool, str]]:
        count = 0
        features = []
        if self._exists('num_brand_logo_appearances'):
            count += self._get('num_brand_logo_appearances', 0)
            features.append(f"num_brand_logo_appearances: {self._get('num_brand_logo_appearances')}")
        if self._exists('num_brand_mentions_in_audio'):
            count += self._get('num_brand_mentions_in_audio', 0)
            features.append(f"num_brand_mentions_in_audio: {self._get('num_brand_mentions_in_audio')}")
        
        features_str = ", ".join(features) if features else "N/A"
        return (features_str, str(count), "SUM(appearances, mentions)", count)

    def _criteria_early_brand_shown(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._exists('product_placement_visually_introduced_time'):
            intro_time = self._get('product_placement_visually_introduced_time')
            if intro_time <= self.wat_threshold:
                return (
                    "product_placement_visually_introduced_time",
                    f"{intro_time}s",
                    f"product_placement_visually_introduced_time <= {self.wat_threshold}s",
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

    def _criteria_humor_playful_tone(self) -> Tuple[str, str, str, Union[bool, str]]:
        if self._is_true('humor'):
            return ("humor", "True", "humor = True", "Humorous")
        
        tone = self._get('tone_of_voice', "")
        appeal = self._get('emotional_appeal', "")
        
        if self._contains_keyword(tone, ["playful", "fun", "joyful", "energetic"]) or \
           self._contains_keyword(appeal, ["playful", "fun", "joyful", "energetic"]):
            return ("tone_of_voice, emotional_appeal", f"{tone}, {appeal}", "Contains playful keywords", "Playful")
        
        if self._contains_keyword(tone, ["calm", "informative", "neutral"]):
            return ("tone_of_voice", tone, "Contains calm/informative keywords", "Neutral")
        
        if self._contains_keyword(appeal, ["safety", "reassurance", "serious"]):
            return ("emotional_appeal", appeal, "Contains safety/reassurance keywords", "Serious")
        
        return ("tone_of_voice, emotional_appeal, humor", f"{tone}, {appeal}, False", "No matching tone", "Ambiguous")

    def get_creative_brand_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria_methods = [
            ("Early Benefit Shown", self._criteria_early_benefit_shown),
            ("First Mention Or Appearance Brand/Logo", self._criteria_first_mention_brand_logo),
            ("Number Mentions Or Appearance Brand/Logo", self._criteria_number_mentions_brand_logo),
            ("Early Brand Shown", self._criteria_early_brand_shown),
            ("Parents Presence", self._criteria_parents_presence),
            ("Editing Tightness", self._criteria_editing_tightness),
            ("Humor/Playful Tone", self._criteria_humor_playful_tone),
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
                traceback.print_exc()
        
        return results

    # ========== META CRITERIA ==========
    
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

    def _meta_safe_zone_top(self) -> Tuple[str, str, str, Union[bool, str]]:
        safe_top = self._get('safe_zone_size_top', 0)
        result = safe_top >= 14
        return ("safe_zone_size_top", f"{safe_top}px", "safe_zone_size_top >= 14", result)

    def _meta_safe_zone_bottom(self) -> Tuple[str, str, str, Union[bool, str]]:
        safe_bottom = self._get('safe_zone_size_bottom', 0)
        result = safe_bottom >= 14
        return ("safe_zone_size_bottom", f"{safe_bottom}px", "safe_zone_size_bottom >= 14", result)

    def _meta_duration_check(self) -> Tuple[str, str, str, Union[bool, str]]:
        duration = self._get('video_duration', 0)
        result = duration >= 1 and duration <= 120
        return ("video_duration", f"{duration}s", "1s <= video_duration <= 120s", result)

    def get_facebook_feed_criteria(self) -> List[CriteriaResult]:
        results = []
        criteria = [
            ("File Type MP4/MOV/GIF", self._meta_file_type_check),
            ("Ratio 1:1 or 4:5", self._meta_ratio_facebook_feed),
            ("Sound Recommended", self._meta_sound_recommended),
            ("Safe Zone Top (14%)", self._meta_safe_zone_top),
            ("Safe Zone Bottom (14%)", self._meta_safe_zone_bottom),
            ("Duration Check", self._meta_duration_check),
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
                traceback.print_exc()
        
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
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Template error: {str(e)}"}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    print("\n" + "="*60)
    print("UPLOAD REQUEST RECEIVED")
    print("="*60)
    
    try:
        # Check if file exists in request
        if 'file' not in request.files:
            print("ERROR: No file in request")
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        print(f"✓ File received: {file.filename}")
        
        # Check if filename is empty
        if file.filename == '':
            print("ERROR: Empty filename")
            return jsonify({"error": "No file selected"}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            print(f"ERROR: File type not allowed - {file.filename}")
            return jsonify({"error": f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
        
        # Get file extension
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        print(f"✓ File extension: {file_ext}")
        
        # Parse file based on extension
        try:
            print(f"→ Parsing as {file_ext.upper()}...")
            
            if file_ext == 'json':
                data = json.load(file)
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                print(f"✓ JSON loaded with {len(data)} keys")
                
            elif file_ext == 'csv':
                df = pd.read_csv(file)
                data = df.iloc[0].to_dict()
                print(f"✓ CSV loaded with {len(data)} columns")
                
            elif file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file)
                data = df.iloc[0].to_dict()
                print(f"✓ Excel loaded with {len(data)} columns")
                
            else:
                print(f"ERROR: Unsupported format - {file_ext}")
                return jsonify({"error": "Unsupported file format"}), 400
                
        except Exception as e:
            print(f"ERROR parsing file: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400
        
        # Get WAT threshold
        wat_threshold = request.form.get('wat_threshold', 2.0, type=float)
        print(f"✓ WAT Threshold: {wat_threshold}")
        
        # Create generator
        print("→ Creating CriteriaGenerator...")
        generator = CriteriaGenerator(wat_threshold=wat_threshold)
        
        # Load data
        print("→ Loading data...")
        if not generator.load_data(data):
            print("ERROR: Failed to load data")
            return jsonify({"error": "Failed to process data"}), 500
        print("✓ Data loaded successfully")
        
        # Get results
        print("→ Generating criteria...")
        results = generator.get_all_results()
        print(f"✓ Generated results for {len(results)} categories")
        
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
            "data": data,
            "results": serialized_results
        })
    
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        traceback.print_exc()
        print("="*60 + "\n")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "OK", "message": "Criteria Generator is running"})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("CRITERIA GENERATOR STARTING")
    print("="*60)
    print("✓ Server running on http://0.0.0.0:5000")
    print("✓ Templates folder: templates/")
    print("✓ Static files folder: static/")
    print("✓ Uploads folder: uploads/")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
