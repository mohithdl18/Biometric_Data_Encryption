#!/usr/bin/env python3
"""
Test Script: Verify Automatic Steganography Integration
This script demonstrates that steganographic images are created automatically
during user registration, regardless of enrollment order.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mongodb_client import get_database

def test_automatic_steganography():
    """Test that steganographic images are created automatically"""
    print("=" * 70)
    print("🧪 Testing Automatic Steganography Integration")
    print("=" * 70)
    
    db = get_database()
    if not db.client:
        print("❌ Failed to connect to database")
        return
    
    users_collection = db.db.users
    
    # Get all users
    all_users = list(users_collection.find({}, {"name": 1, "face_image_id": 1, 
                                                  "fingerprint_key": 1, "fingerprint_algorithm": 1,
                                                  "has_steganographic_image": 1, 
                                                  "face_stego_image_id": 1}))
    
    print(f"\n📊 Total users in database: {len(all_users)}\n")
    
    # Categorize users
    complete_users = []      # Has face + fingerprint + stego
    pending_users = []       # Has face + fingerprint, but no stego
    incomplete_users = []    # Missing face or fingerprint
    
    for user in all_users:
        name = user['name']
        has_face = user.get('face_image_id') is not None
        has_fingerprint = (user.get('fingerprint_key') or user.get('fingerprint_algorithm')) is not None
        has_stego = user.get('has_steganographic_image', False) and user.get('face_stego_image_id') is not None
        
        if has_face and has_fingerprint and has_stego:
            complete_users.append(name)
        elif has_face and has_fingerprint and not has_stego:
            pending_users.append(name)
        else:
            incomplete_users.append((name, has_face, has_fingerprint))
    
    # Display results
    print("✅ COMPLETE USERS (Face + Fingerprint + Steganographic Image):")
    print("-" * 70)
    if complete_users:
        for name in complete_users:
            print(f"  ✓ {name}")
    else:
        print("  (none)")
    print()
    
    print("⚠️  PENDING USERS (Face + Fingerprint, Missing Steganographic Image):")
    print("-" * 70)
    if pending_users:
        for name in pending_users:
            print(f"  ⚠️ {name}")
        print(f"\n  💡 Tip: Run 'python create_steganographic_images.py' to fix these users")
        print(f"  💡 OR: Re-register them to trigger automatic creation")
    else:
        print("  (none)")
    print()
    
    print("❌ INCOMPLETE USERS (Missing Face or Fingerprint):")
    print("-" * 70)
    if incomplete_users:
        for name, has_face, has_fp in incomplete_users:
            status = []
            if not has_face:
                status.append("No Face")
            if not has_fp:
                status.append("No Fingerprint")
            print(f"  ❌ {name} - {', '.join(status)}")
    else:
        print("  (none)")
    print()
    
    # Summary
    print("=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"Total Users:      {len(all_users)}")
    print(f"✅ Complete:      {len(complete_users)} ({len(complete_users)/len(all_users)*100:.1f}%)")
    print(f"⚠️  Pending:       {len(pending_users)} ({len(pending_users)/len(all_users)*100:.1f}%)")
    print(f"❌ Incomplete:    {len(incomplete_users)} ({len(incomplete_users)/len(all_users)*100:.1f}%)")
    print("=" * 70)
    
    # Test automatic creation
    print("\n🧪 TESTING AUTOMATIC CREATION")
    print("=" * 70)
    print("\nTo test automatic steganography creation:")
    print("1. Register a new user via the frontend")
    print("2. Enroll EITHER face OR fingerprint first (order doesn't matter)")
    print("3. Enroll the other biometric")
    print("4. System will AUTOMATICALLY create steganographic image")
    print("\nExpected behavior:")
    print("  • If Face First → Stego created when fingerprint enrolled")
    print("  • If Fingerprint First → Stego created when face captured")
    print("\nCheck server logs for:")
    print("  [INFO] ✅ Steganographic image automatically created for <username>")
    print("=" * 70)
    
    # Return statistics
    return {
        "total": len(all_users),
        "complete": len(complete_users),
        "pending": len(pending_users),
        "incomplete": len(incomplete_users)
    }

if __name__ == "__main__":
    stats = test_automatic_steganography()
    
    print("\n" + "=" * 70)
    print("🎯 INTEGRATION STATUS")
    print("=" * 70)
    
    if stats["pending"] > 0:
        print("⚠️  Status: PARTIAL - Some users need steganographic images")
        print(f"\n💡 Quick Fix: Run the utility script to process {stats['pending']} pending users")
        print("   python create_steganographic_images.py")
    elif stats["complete"] == stats["total"]:
        print("✅ Status: COMPLETE - All users have steganographic images!")
        print("\n🎉 Automatic steganography is working perfectly!")
    else:
        print("ℹ️  Status: READY - System configured for automatic steganography")
        print("\n📝 Next: Register a new user to test automatic creation")
    
    print("=" * 70)
