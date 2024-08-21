import uuid
import firebase_admin
from firebase_admin import credentials, storage
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from blueprints.auth import token_required, db

posts_bp = Blueprint('posts', __name__)
posts_collection = db['posts']
cred = credentials.Certificate("influential-kit-430506-m-45094-firebase-adminsdk-3gh5f-4781881dca.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'influential-kit-430506-m-45094.appspot.com'
})
bucket = storage.bucket()


@posts_bp.route('/posts/<id>', methods=['GET'])
@token_required
def get_post(current_user, id):
    try:
        if not ObjectId.is_valid(id):
            return jsonify({'error': 'Invalid ObjectId format'}), 400

        post = posts_collection.find_one({'_id': ObjectId(id)})
        if post:
            post['_id'] = str(post['_id'])  # Convert ObjectId to string for JSON serialization
            post['author_id'] = str(post['author_id'])
            return jsonify(post), 200
        else:
            return jsonify({'error': 'Post not found'}), 404
    except Exception as e:
        return jsonify({'Error': str(e)}), 500  # Internal server error

@posts_bp.route('/posts', methods=['POST'])
@token_required
def create_post(current_user):
    file = request.files.get('thumbnail')
    title = request.form.get('title')
    text = request.form.get("text")
    tags = request.form.get("tags")

    # Validate form data
    if not title or not text or not tags:
        return jsonify({"error": "Invalid input"}), 400


    if not file:
        return jsonify({"error": "No file provided"}), 400

    # Upload the thumbnail to Firebase Storage
    try:
        file_id = str(uuid.uuid4())
        blob = bucket.blob(file_id)
        blob.upload_from_file(file, content_type=file.content_type)

        # Get the public URL of the uploaded file
        thumbnail_url = blob.public_url
    except Exception as e:
        return jsonify({'error': 'Failed to upload thumbnail: ' + str(e)}), 500

    # Prepare post data
    post_data = {
        'title': title,
        "text": text,
        "tags": [tags] if isinstance(tags, str) else tags,
        "comments": [],
        "likes": 0,
        "dislikes": 0,
        'author_id': current_user['_id'],
        'created_at': datetime.utcnow(),
        'thumbnail_url': thumbnail_url  # Save the URL of the uploaded thumbnail
    }

    # Insert the post into the database
    try:
        result = posts_collection.insert_one(post_data)
        post_id = result.inserted_id

        return jsonify({
            "message": "Post created successfully",
            "Post ID": str(post_id),
            "Post Title": post_data['title'],
            "Post Data": post_data['text'],
            "Post Tags": post_data['tags'],
            "Thumbnails Url": post_data['thumbnail_url']
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Internal server error


@posts_bp.route('/posts/<post_id>', methods=['PUT'])
@token_required
def update_post(current_user, post_id):
    global file
    update_data = {}
    try:
        file = request.files.get('thumbnail')
        title = request.form.get('title')
        text = request.form.get("text")
        tags = request.form.get("tags")
        comment = request.form.get("comments")
        if title:
            update_data["title"] = title
        if text:
            update_data["text"] = text
        if tags:
            update_data['tags'] = [tags]
        if comment:
            update_data['comments'] = comment
        print(update_data)
    except:
        print("invalid input")
    try:
        file_id = str(uuid.uuid4())
        blob = bucket.blob(file_id)
        blob.upload_from_file(file, content_type=file.content_type)

        # Get the public URL of the uploaded file
        thumbnail_url = blob.public_url
        update_data['thumbnail_url'] = thumbnail_url
        print(thumbnail_url)
    except:
        print("file not found")

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        result = posts_collection.update_one({"_id": ObjectId(post_id), 'author_id': current_user['_id']},
                                             {"$set": update_data})
        if result.modified_count > 0:
            return jsonify({"message": "Post updated successfully"}), 200
        else:
            return jsonify({"error": "No changes made to the post"}), 304
    except Exception as e:
        return jsonify({"error": "Failed to update post"}), 500


@posts_bp.route('/posts/<post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    post = posts_collection.find_one({'_id': ObjectId(post_id), 'author_id': current_user['_id']})

    if not post:
        return jsonify({'error': 'Post not found or you are not the author'}), 404

    posts_collection.delete_one({'_id': ObjectId(post_id)})
    return jsonify({'message': 'Post deleted successfully'}), 200


@posts_bp.route("/posts/comments/<post_id>", methods=["POST"])
@token_required
def add_comments(current_user, post_id):
    comments = request.form.get("comments")
    if not comments:
        return jsonify({"error": "Missing comments in request"}), 400

    try:
        post = posts_collection.find_one({'_id': ObjectId(post_id), 'author_id': current_user['_id']})
        if post:
            if "comments" not in post:
                posts_collection.update_one({"_id": ObjectId(post_id)}, {"$set": {"comments": []}})
            try:
                result = posts_collection.update_one({"_id": ObjectId(post_id)}, {"$push": {"comments": comments}})
                return jsonify({"message": "Comments added successfully"}), 200
            except Exception as e:
                return jsonify({"error": "Failed to add comments"}), 500
        else:
            return jsonify({"error": "Post not found or you are not the author"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@posts_bp.route("/posts/comments/<post_id>", methods=["DELETE"])
@token_required
def delete_comments(current_user, post_id):
    comments = request.form.get("comments")
    if not comments:
        return jsonify({"error": "Missing comments in request"}), 400

    try:
        result = posts_collection.update_one({"_id": ObjectId(post_id)}, {"$pull": {"comments": comments}})
        if result.modified_count > 0:
            return jsonify({"message": "Comments deleted successfully"}), 200
        else:
            return jsonify({"error": "No comments deleted"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@posts_bp.route("/posts/comments/<post_id>", methods=["PUT"])
@token_required
def update_comments(current_user, post_id):
    pre_comment = request.form.get("pre_comment")
    new_comment = request.form.get("new_comment")

    if not pre_comment or not new_comment:
        return jsonify({"error": "Missing pre_comment or new_comment in request"}), 400

    try:
        result = posts_collection.update_one({"_id": ObjectId(post_id), "comments": pre_comment},
                                             {"$set": {"comments.$": new_comment}})
        if result.modified_count > 0:
            return jsonify({"message": "Comment updated successfully"}), 200
        else:
            return jsonify({"error": "Comment not found or not updated"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@posts_bp.route("/posts/reactions/<post_id>", methods=["PUT"])
@token_required
def post_reaction(current_user, post_id):

    action = request.form.get("action")

    if action not in ['like', 'dislike']:
        return jsonify({"error": "Invalid action. Use 'like' or 'dislike'"}), 400

    try:
        if action == 'like':
            result = posts_collection.update_one({"_id": ObjectId(post_id)}, {"$inc": {"likes": 1}})
            if result.modified_count > 0:
                return jsonify({"message": "Like added successfully"}), 200
            else:
                return jsonify({"error": "Like not added"}), 404
        elif action == 'dislike':
            result = posts_collection.update_one({"_id": ObjectId(post_id)}, {"$inc": {"dislikes": 1}})
            if result.modified_count > 0:
                return jsonify({"message": "Dislike added successfully"}), 200
            else:
                return jsonify({"error": "Dislike not added"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500