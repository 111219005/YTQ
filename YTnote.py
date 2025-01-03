from flask import Flask, request, jsonify
import random
import spacy
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

nlp = spacy.load("en_core_web_sm")
users = {}

def get_video_subtitles(video_url):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        return {"subtitles": formatter.format_transcript(transcript)}
    except Exception as e:
        return {"error": f"Could not retrieve subtitles. Error: {str(e)}"}

def create_knowledge_question(sent_doc):
    # 找出關鍵資訊
    key_info = []
    for token in sent_doc:
        if token.pos_ in ["NOUN", "PROPN", "NUM"] and token.dep_ in ["nsubj", "dobj", "pobj"]:
            key_info.append(token.text)
    
    if key_info:
        # 替換關鍵詞生成填空題
        text = sent_doc.text
        answer = random.choice(key_info)
        question = text.replace(answer, "_____")
        return f"Fill in the blank: {question}\nAnswer: {answer}"
    return None

def create_true_false_question(sent):
    # 生成是非題
    return f"True or False: {sent}\nAnswer: True"

def create_explanation_question(sent):
    # 生成解釋題
    return f"Explain this statement: {sent}"

def generate_questions_from_subtitles(subtitles):
    if "error" in subtitles:
        return ["Error generating questions: " + subtitles["error"]]
    
    doc = nlp(subtitles["subtitles"])
    sentences = list(doc.sents)
    questions = []
    
    # 選擇有意義的句子
    meaningful_sents = [
        sent for sent in sentences 
        if len(sent.text.split()) > 5 and
        any(token.pos_ in ["NOUN", "VERB", "NUM"] for token in sent)
    ]
    
    if len(meaningful_sents) > 5:
        meaningful_sents = random.sample(meaningful_sents, 5)
    
    for sent in meaningful_sents:
        # 隨機選擇問題類型
        question_types = [
            lambda s: create_knowledge_question(s),
            lambda s: create_true_false_question(s.text),
            lambda s: create_explanation_question(s.text)
        ]
        
        question_func = random.choice(question_types)
        question = question_func(sent)
        if question:
            questions.append(question)
    
    return questions


@app.route("/login", methods=["POST"])
def login():
    user_id = request.json.get("user_id")
    age = request.json.get("age")
    
    if not user_id or not age:
        return jsonify({"error": "Missing user information."}), 400
    
    users[user_id] = {"age": age}
    return jsonify({"message": "User logged in successfully."}), 200

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz_endpoint():
    user_id = request.json.get("user_id")
    video_url = request.json.get("video_url")
    
    if not user_id or not video_url:
        return jsonify({"error": "Missing user ID or video URL."}), 400
    
    if user_id not in users:
        return jsonify({"error": "User not logged in."}), 404
    
    subtitles = get_video_subtitles(video_url)
    questions = generate_questions_from_subtitles(subtitles)
    
    return jsonify({"quiz": questions}), 200

@app.route("/view_users", methods=["GET"])
def view_users():
    return jsonify(users), 200

if __name__ == "__main__":
    app.run(debug=True)