# 🗄️ Steganographic Image Database Storage

## MongoDB Atlas Database Structure

### Database Name: `biometric_db`

### Collection 1: `users`
This collection stores user information and references to images.

**User Document Example:**
```json
{
  "_id": ObjectId("691b0f16ca0077bc1c64b354"),
  "name": "MOHITH D L",
  "email": "mohithdl1803@gmail.com",
  "phone": "1234567890",
  "created_at": ISODate("2025-11-17T..."),
  
  // ORIGINAL FACE IMAGE REFERENCE
  "face_image_id": ObjectId("691b0f18ca0077bc1c64b356"),
  
  // STEGANOGRAPHIC IMAGE REFERENCE (only if fingerprint was enrolled BEFORE face capture)
  "face_stego_image_id": ObjectId("691b0f18ca0077bc1c64b357"),
  "has_steganographic_image": true,
  
  // Fingerprint data
  "fingerprint_template": "base64_encoded_template_data",
  "fingerprint_key": "fcf0aea289944f5d...3fc69b023a3e55ff",
  "fingerprint_algorithm": "sha256",
  
  // Timestamps
  "face_updated_at": ISODate("2025-11-17T..."),
  "fingerprint_updated_at": ISODate("2025-11-17T...")
}
```

### Collection 2: `fs.files` (GridFS Metadata)
GridFS stores large files (images) in chunks. The metadata is in `fs.files`.

**Original Image Metadata:**
```json
{
  "_id": ObjectId("691b0f18ca0077bc1c64b356"),
  "length": 45632,
  "chunkSize": 261120,
  "uploadDate": ISODate("2025-11-17T12:33:39.123Z"),
  "filename": "MOHITH D L_original_face_001.jpg",
  "contentType": "image/png",
  "metadata": {
    "user_name": "MOHITH D L",
    "type": "face_image_original",
    "upload_date": ISODate("2025-11-17T12:33:39.123Z")
  }
}
```

**Steganographic Image Metadata:**
```json
{
  "_id": ObjectId("691b0f18ca0077bc1c64b357"),
  "length": 48256,
  "chunkSize": 261120,
  "uploadDate": ISODate("2025-11-17T12:33:39.456Z"),
  "filename": "MOHITH D L_steganographic_face_001.jpg",
  "contentType": "image/png",
  "metadata": {
    "user_name": "MOHITH D L",
    "type": "face_image_steganographic",
    "has_embedded_key": true,
    "upload_date": ISODate("2025-11-17T12:33:39.456Z")
  }
}
```

### Collection 3: `fs.chunks` (GridFS Data Chunks)
This stores the actual binary image data in 255KB chunks.

**Example Chunk:**
```json
{
  "_id": ObjectId("691b0f18ca0077bc1c64b358"),
  "files_id": ObjectId("691b0f18ca0077bc1c64b357"),  // References steganographic image
  "n": 0,  // Chunk number
  "data": BinData(0, "iVBORw0KGgoAAAANSUhEUgAA...")  // Binary PNG data with hidden key
}
```

---

## 🔍 How to Find Steganographic Images in MongoDB

### Using MongoDB Compass or Atlas:

1. **Connect to your database:**
   - Database: `biometric_db`

2. **Check if user has steganographic image:**
   ```javascript
   // In users collection
   db.users.find({
     "name": "MOHITH D L",
     "has_steganographic_image": true
   })
   ```

3. **View steganographic image metadata:**
   ```javascript
   // In fs.files collection
   db.fs.files.find({
     "metadata.type": "face_image_steganographic",
     "metadata.user_name": "MOHITH D L"
   })
   ```

4. **View all steganographic images:**
   ```javascript
   db.fs.files.find({
     "metadata.type": "face_image_steganographic"
   })
   ```

---

## ⚠️ Current Issue with Your User

Looking at the server logs, I see:

```
✅ Original face image saved for MOHITH D L
✅ Face image(s) saved for user: MOHITH D L (original only)
```

**Why no steganographic image?**
- Face was captured FIRST
- Then fingerprint was enrolled
- Steganographic image is only created when fingerprint key exists **BEFORE** face capture

**User data in MongoDB:**
```json
{
  "_id": "691b0f16ca0077bc1c64b354",
  "name": "MOHITH D L",
  "face_image_id": ObjectId("..."),           // ✅ Exists
  "face_stego_image_id": NOT PRESENT,          // ❌ Missing
  "has_steganographic_image": NOT PRESENT,     // ❌ Missing
  "fingerprint_key": "fcf0aea289944f5d..."    // ✅ Exists (but enrolled AFTER face)
}
```

---

## ✅ How to Fix This

### Option 1: Re-capture Face Image (Recommended)

1. **Delete current user** from admin panel
2. **Register new user**
3. **Enroll FINGERPRINT FIRST** ⚠️ Important!
4. **Then capture face image**
5. System will automatically create steganographic version

### Option 2: Use Python Script to Generate Steganographic Image

I can create a script that:
- Retrieves existing face image
- Gets fingerprint key
- Creates steganographic version
- Saves it to database

---

## 📝 Database Fields Summary

### In `users` collection:

| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `face_image_id` | ObjectId | Reference to original image in GridFS | `ObjectId("691b...")` |
| `face_stego_image_id` | ObjectId | Reference to steganographic image in GridFS | `ObjectId("691c...")` |
| `has_steganographic_image` | Boolean | Flag indicating stego image exists | `true` |
| `fingerprint_key` | String | SHA-256 key embedded in stego image | `"fcf0aea2..."` (64 chars) |

### In `fs.files` collection:

| Field | Type | Description |
|-------|------|-------------|
| `metadata.type` | String | `"face_image_original"` or `"face_image_steganographic"` |
| `metadata.has_embedded_key` | Boolean | `true` for steganographic images |
| `metadata.user_name` | String | Username for reference |

### In `fs.chunks` collection:

| Field | Type | Description |
|-------|------|-------------|
| `files_id` | ObjectId | References `_id` in `fs.files` |
| `data` | Binary | Actual PNG image data (with hidden key for stego images) |

---

## 🔍 MongoDB Queries Cheat Sheet

### Find users with steganographic images:
```javascript
db.users.find({ "has_steganographic_image": true })
```

### Find all steganographic image files:
```javascript
db.fs.files.find({ "metadata.type": "face_image_steganographic" })
```

### Find steganographic image for specific user:
```javascript
// Step 1: Get user's stego image ID
var user = db.users.findOne({ "name": "USERNAME" })
var stegoImageId = user.face_stego_image_id

// Step 2: Get image metadata
db.fs.files.findOne({ "_id": stegoImageId })

// Step 3: Get image chunks (binary data)
db.fs.chunks.find({ "files_id": stegoImageId }).sort({ "n": 1 })
```

### Count steganographic images:
```javascript
db.fs.files.countDocuments({ "metadata.type": "face_image_steganographic" })
```

---

## 🎯 Summary

**Storage Location:**
- **Database**: `biometric_db` on MongoDB Atlas
- **User Reference**: `users` collection → `face_stego_image_id` field
- **Image Metadata**: `fs.files` collection (GridFS)
- **Image Data**: `fs.chunks` collection (Binary PNG with embedded key)

**Your Current Status:**
- ❌ No steganographic image for "MOHITH D L"
- ✅ Face image exists (original only)
- ✅ Fingerprint key exists
- ⚠️ Need to re-register with fingerprint BEFORE face

**Next Steps:**
1. Delete user "MOHITH D L"
2. Register again
3. Enroll fingerprint FIRST
4. Then capture face
5. Check dashboard - steganographic download will appear!
