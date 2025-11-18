/**
 * AI Cross-Poster Mobile App
 * React Native / Expo App with Camera Integration
 *
 * Features:
 * - Camera integration for taking photos
 * - AI-powered listing generation
 * - Post to eBay and Mercari
 * - Storage location tracking
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Image,
  Alert,
  ActivityIndicator,
  SafeAreaView,
  Platform,
} from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

// API Configuration
const API_BASE_URL = 'http://localhost:8000'; // Change to your server URL in production

interface Photo {
  photo_id: string;
  url: string;
  local_path: string;
  uri: string;
}

interface AIAnalysis {
  title: string;
  description: string;
  suggested_price?: number;
  brand?: string;
  size?: string;
  color?: string;
  condition: string;
  category?: string;
}

export default function App() {
  // State
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraType, setCameraType] = useState(CameraType.back);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [posting, setPosting] = useState(false);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [cost, setCost] = useState('');
  const [brand, setBrand] = useState('');
  const [size, setSize] = useState('');
  const [color, setColor] = useState('');
  const [storageLocation, setStorageLocation] = useState('');
  const [condition, setCondition] = useState('excellent');
  const [selectedPlatforms, setSelectedPlatforms] = useState({
    ebay: true,
    mercari: true,
  });

  const cameraRef = useRef<Camera>(null);

  // Request permissions
  useEffect(() => {
    (async () => {
      const { status: cameraStatus } = await Camera.requestCameraPermissionsAsync();
      const { status: mediaStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      setHasPermission(cameraStatus === 'granted' && mediaStatus === 'granted');
    })();
  }, []);

  // Take photo with camera
  const takePicture = async () => {
    if (cameraRef.current) {
      try {
        const photo = await cameraRef.current.takePictureAsync();
        await uploadPhoto(photo.uri);
        setShowCamera(false);
      } catch (error) {
        Alert.alert('Error', 'Failed to take picture');
        console.error(error);
      }
    }
  };

  // Pick photo from gallery
  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsMultipleSelection: true,
        quality: 0.8,
      });

      if (!result.canceled) {
        for (const asset of result.assets) {
          await uploadPhoto(asset.uri);
        }
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to pick image');
      console.error(error);
    }
  };

  // Upload photo to server
  const uploadPhoto = async (uri: string) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', {
        uri,
        type: 'image/jpeg',
        name: 'photo.jpg',
      } as any);

      const response = await axios.post(
        `${API_BASE_URL}/photos/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            Authorization: 'Bearer demo_token', // Replace with actual auth token
          },
        }
      );

      setPhotos([...photos, { ...response.data, uri }]);
      Alert.alert('Success', 'Photo uploaded!');
    } catch (error) {
      Alert.alert('Error', 'Failed to upload photo');
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  // Analyze photos with AI
  const analyzeWithAI = async () => {
    if (photos.length === 0) {
      Alert.alert('No Photos', 'Please add photos first!');
      return;
    }

    setAnalyzing(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/ai/analyze`,
        {
          photo_ids: photos.map(p => p.photo_id),
          enable_gpt4_fallback: false,
        },
        {
          headers: {
            Authorization: 'Bearer demo_token',
          },
        }
      );

      const analysis: AIAnalysis = response.data;

      // Auto-fill form with AI analysis
      setTitle(analysis.title);
      setDescription(analysis.description);
      if (analysis.suggested_price) {
        setPrice(analysis.suggested_price.toString());
      }
      if (analysis.brand) setBrand(analysis.brand);
      if (analysis.size) setSize(analysis.size);
      if (analysis.color) setColor(analysis.color);
      setCondition(analysis.condition);

      Alert.alert('Success', 'AI analysis complete! Review the generated listing.');
    } catch (error) {
      Alert.alert('Error', 'Failed to analyze photos');
      console.error(error);
    } finally {
      setAnalyzing(false);
    }
  };

  // Post listing
  const postListing = async () => {
    if (!title || !price || photos.length === 0) {
      Alert.alert('Missing Info', 'Please add photos, title, and price!');
      return;
    }

    const platforms = Object.entries(selectedPlatforms)
      .filter(([_, selected]) => selected)
      .map(([platform]) => platform);

    if (platforms.length === 0) {
      Alert.alert('No Platforms', 'Please select at least one platform!');
      return;
    }

    setPosting(true);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/listings/create`,
        {
          title,
          description,
          price: parseFloat(price),
          cost: cost ? parseFloat(cost) : null,
          condition,
          photo_ids: photos.map(p => p.photo_id),
          brand: brand || null,
          size: size || null,
          color: color || null,
          storage_location: storageLocation || null,
          shipping_cost: 0,
          platforms,
        },
        {
          headers: {
            Authorization: 'Bearer demo_token',
          },
        }
      );

      Alert.alert(
        'Success!',
        `Posted to ${response.data.success_count}/${response.data.total_platforms} platforms!\n\nListing ID: ${response.data.listing_id}`,
        [
          {
            text: 'OK',
            onPress: () => {
              // Clear form
              setPhotos([]);
              setTitle('');
              setDescription('');
              setPrice('');
              setCost('');
              setBrand('');
              setSize('');
              setColor('');
              setStorageLocation('');
            },
          },
        ]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to post listing');
      console.error(error);
    } finally {
      setPosting(false);
    }
  };

  if (hasPermission === null) {
    return <View style={styles.container}><Text>Requesting permissions...</Text></View>;
  }

  if (hasPermission === false) {
    return <View style={styles.container}><Text>No access to camera</Text></View>;
  }

  if (showCamera) {
    return (
      <View style={styles.container}>
        <Camera style={styles.camera} type={cameraType} ref={cameraRef}>
          <View style={styles.cameraButtons}>
            <TouchableOpacity
              style={styles.button}
              onPress={() => setShowCamera(false)}>
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
              <View style={styles.captureButtonInner} />
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.button}
              onPress={() => {
                setCameraType(
                  cameraType === CameraType.back ? CameraType.front : CameraType.back
                );
              }}>
              <Text style={styles.buttonText}>Flip</Text>
            </TouchableOpacity>
          </View>
        </Camera>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>📦 AI Cross-Poster</Text>
          <Text style={styles.subtitle}>Snap, List, Sell!</Text>
        </View>

        {/* Photo Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Photos ({photos.length})</Text>

          <ScrollView horizontal style={styles.photoScroll}>
            {photos.map((photo, index) => (
              <View key={index} style={styles.photoContainer}>
                <Image source={{ uri: photo.uri }} style={styles.photoThumbnail} />
                <TouchableOpacity
                  style={styles.removeButton}
                  onPress={() => setPhotos(photos.filter((_, i) => i !== index))}>
                  <Text style={styles.removeButtonText}>×</Text>
                </TouchableOpacity>
              </View>
            ))}
          </ScrollView>

          <View style={styles.buttonRow}>
            <TouchableOpacity
              style={[styles.actionButton, styles.primaryButton]}
              onPress={() => setShowCamera(true)}
              disabled={uploading}>
              <Text style={styles.actionButtonText}>📷 Take Photo</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.secondaryButton]}
              onPress={pickImage}
              disabled={uploading}>
              <Text style={styles.actionButtonText}>🖼️ Gallery</Text>
            </TouchableOpacity>
          </View>

          {uploading && <ActivityIndicator style={styles.loader} />}
        </View>

        {/* AI Analysis Button */}
        {photos.length > 0 && (
          <TouchableOpacity
            style={[styles.actionButton, styles.aiButton]}
            onPress={analyzeWithAI}
            disabled={analyzing}>
            <Text style={styles.actionButtonText}>
              {analyzing ? '🔄 Analyzing...' : '🤖 Analyze with AI'}
            </Text>
          </TouchableOpacity>
        )}

        {/* Listing Details Form */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Listing Details</Text>

          <TextInput
            style={styles.input}
            placeholder="Title"
            value={title}
            onChangeText={setTitle}
            maxLength={80}
          />

          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Description"
            value={description}
            onChangeText={setDescription}
            multiline
            numberOfLines={4}
          />

          <View style={styles.row}>
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Price ($)"
              value={price}
              onChangeText={setPrice}
              keyboardType="decimal-pad"
            />
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Cost ($)"
              value={cost}
              onChangeText={setCost}
              keyboardType="decimal-pad"
            />
          </View>

          <View style={styles.row}>
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Brand"
              value={brand}
              onChangeText={setBrand}
            />
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Size"
              value={size}
              onChangeText={setSize}
            />
          </View>

          <View style={styles.row}>
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Color"
              value={color}
              onChangeText={setColor}
            />
            <TextInput
              style={[styles.input, styles.halfInput]}
              placeholder="Storage (e.g., A1)"
              value={storageLocation}
              onChangeText={setStorageLocation}
            />
          </View>
        </View>

        {/* Platform Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Post To</Text>
          <View style={styles.platformRow}>
            <TouchableOpacity
              style={[
                styles.platformButton,
                selectedPlatforms.ebay && styles.platformButtonActive,
              ]}
              onPress={() =>
                setSelectedPlatforms({ ...selectedPlatforms, ebay: !selectedPlatforms.ebay })
              }>
              <Text style={styles.platformButtonText}>eBay</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.platformButton,
                selectedPlatforms.mercari && styles.platformButtonActive,
              ]}
              onPress={() =>
                setSelectedPlatforms({
                  ...selectedPlatforms,
                  mercari: !selectedPlatforms.mercari,
                })
              }>
              <Text style={styles.platformButtonText}>Mercari</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Post Button */}
        <TouchableOpacity
          style={[styles.actionButton, styles.postButton]}
          onPress={postListing}
          disabled={posting}>
          <Text style={styles.postButtonText}>
            {posting ? '⏳ Posting...' : '🚀 Post Listing'}
          </Text>
        </TouchableOpacity>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    padding: 20,
    paddingTop: Platform.OS === 'ios' ? 40 : 20,
    backgroundColor: '#2a2a2a',
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 16,
    color: '#aaa',
    marginTop: 5,
  },
  section: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 15,
  },
  photoScroll: {
    marginBottom: 15,
  },
  photoContainer: {
    position: 'relative',
    marginRight: 10,
  },
  photoThumbnail: {
    width: 100,
    height: 100,
    borderRadius: 8,
  },
  removeButton: {
    position: 'absolute',
    top: -5,
    right: -5,
    backgroundColor: '#ff4444',
    width: 25,
    height: 25,
    borderRadius: 12.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  removeButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginVertical: 10,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: '#4CAF50',
    marginRight: 10,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: '#2196F3',
  },
  aiButton: {
    backgroundColor: '#9C27B0',
    marginHorizontal: 20,
  },
  postButton: {
    backgroundColor: '#FF6B00',
    marginHorizontal: 20,
    marginTop: 10,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  postButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  input: {
    backgroundColor: '#2a2a2a',
    color: '#fff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    fontSize: 16,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    flex: 1,
    marginRight: 5,
  },
  platformRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  platformButton: {
    flex: 1,
    padding: 15,
    borderRadius: 8,
    backgroundColor: '#333',
    alignItems: 'center',
    marginHorizontal: 5,
  },
  platformButtonActive: {
    backgroundColor: '#4CAF50',
  },
  platformButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  loader: {
    marginTop: 10,
  },
  camera: {
    flex: 1,
  },
  cameraButtons: {
    flex: 1,
    backgroundColor: 'transparent',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    padding: 20,
  },
  button: {
    padding: 15,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 8,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  captureButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#ff4444',
  },
  bottomPadding: {
    height: 50,
  },
});
