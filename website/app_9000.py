from flask import Flask, request, jsonify, render_template
import getpass
import base64
from model.model import generate_story, text_translations, text_to_images, text_to_speeches, translate_to_eng
import firebase_admin
from firebase_admin import credentials, storage
from io import BytesIO
from PIL import Image
import random
import string
import os
import json
from datetime import timedelta
import shutil


app = Flask(__name__)

#  firebase
cred = credentials.Certificate("/home/webapp/AI_PictureBooks_Web/website/templates/firebaseconfig.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'mywebsite-vivian.appspot.com'
})
bucket = storage.bucket()

# db=firestore.client()
# collection_ref = db.collection('item')
# doc_ref = collection_ref.add("shi")

"""Define Flask routes"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/project')
def project():
    return render_template('project.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/test_input')
def test():
    return render_template('submit.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    title = data.get('title')
    language = data.get('language')  # es
    token = data.get('token')  # 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
    uid = data.get('uid')
    storyToken = data.get('storyToken')



    # story_info = {'paragraph 1': "I was an ordinary boy, but one day I found a strange object in the forest. It was a toad's leg bone and it glowed with magic!", 'illustration 1': "A young boy holding a glowing toad's leg bone, standing in front of a giant tree. The background is filled with colorful leaves and flowers.", 'paragraph 2': 'When I touched the bone, I felt strange powers coursing through my body. Suddenly, I grew scales, wings, and a fiery breath!', 'illustration 2': 'A boy transformed into a dragon, standing on his hind legs with wings spread wide. He is surrounded by flames and smoke.', 'paragraph 3': 'Now I can breathe fire and fly through the skies! People call me the Spit Dragon because of my fiery breath. But sometimes I miss being a human boy.', 'illustration 3': 'A dragon flying over a village, with people looking up in amazement. The dragon has a sad expression on his face, longing for his former life as a human.', 'paragraph 4': "One day, I will find a way to turn back into a boy. Until then, I'll soar the skies and protect my forest home with my fiery breath!", 'illustration 4': 'A dragon perched on a branch of a tree, looking out over the landscape with a determined expression. The sun is setting in the background, casting warm colors across the scene.', 'title': 'I became a spit dragon'}
    title_eng = translate_to_eng(title)
    story_info = generate_story(title)
    translation = text_translations(story_info, language)
    image = text_to_images(story_info, token)
    speeches = text_to_speeches(translation, language)
    

    story_data = {
        'title': title,
        'story': story_info,
        'translation': translation
    }
    json_blob = bucket.blob(f'{title_eng}/{title_eng}.json')
    json_blob.upload_from_string(json.dumps(story_data), content_type='application/json')
    json_url = json_blob.generate_signed_url(timedelta(days=365))


    image_url = []
    for i, img in enumerate(image):
        img_bytes = BytesIO()
        try:
            img.save(img_bytes, format='PNG')
        except Exception as e:
            print(f"Error saving image {i}: {e}")
            continue
        img_bytes.seek(0)
        blob = bucket.blob(f'{title_eng}/image_{i}.jpg')
        blob.upload_from_file(img_bytes, content_type='image/jpg')
        image_url.append(blob.generate_signed_url(timedelta(days=365)))

    mp3_urls = []
    for i, speech_file in enumerate(speeches):
        blob = bucket.blob(f'{title_eng}/paragraph_{i}.mp3')
        blob.upload_from_filename(speech_file)
        mp3_token = blob.generate_signed_url(timedelta(days=365))
        mp3_urls.append(mp3_token)
    for i in range(4):
        i = i + 1
        os.remove(f'/home/webapp/AI_PictureBooks_Web/website/model/speech/paragraph {i}.mp3')


    log_blob = bucket.blob('story_logs.json')
    log_data = json.loads(log_blob.download_as_text()) if log_blob.exists() else []
    log_entry = {
        'title': title,
        'title_eng': title_eng,
        'story_url': json_url,
        'image_urls': image_url,
        'speech_urls': mp3_urls
    }
    log_data.append(log_entry)
    log_blob.upload_from_string(json.dumps(log_data), content_type='application/json')
    
    db=firestore.client()
    collection_ref = db.collection('item')
    doc_ref = collection_ref.add("shi")
    
    
    # https://firebasestorage.googleapis.com/v0/b/webapp-ecc1b.appspot.com/o/story_logs.json?alt=media&token=1560ce88-e76f-473f-a38d-d7caec27c511

    # return jsonify({'story': json_url,'image_urls': image_url})
    # return jsonify({'speech': mp3_urls})
    return jsonify({'story': json_url,'image_urls': image_url,'speech': mp3_urls})

if __name__ == "__main__":
    app.run(debug=True, port=9000)