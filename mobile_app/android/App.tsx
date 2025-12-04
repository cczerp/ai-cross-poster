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
  FlatList,
  Modal,
} from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { BarCodeScanner } from 'expo-barcode-scanner';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import * as Clipboard from 'expo-clipboard';
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

interface InventoryItem {
  id: string;
  title: string;
  storage_location: string;
  photos: Photo[];
  created_at: string;
}

interface ListingTemplate {
  id: string;
  name: string;
  title: string;
  description: string;
  brand?: string;
  size?: string;
  color?: string;
  condition: string;
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

  // New mobile features state
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);
  const [scannedBarcode, setScannedBarcode] = useState('');
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [templates, setTemplates] = useState<ListingTemplate[]>([]);
  const [showInventory, setShowInventory] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<'camera' | 'inventory' | 'templates'>('camera');

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

  // ===== NEW MOBILE FEATURES =====

  // Barcode Scanning
  const requestBarcodePermission = async () => {
    const { status } = await BarCodeScanner.requestPermissionsAsync();
    return status === 'granted';
  };

  const handleBarCodeScanned = ({ type, data }: { type: string; data: string }) => {
    setScannedBarcode(data);
    setShowBarcodeScanner(false);
    Alert.alert('Barcode Scanned', `Type: ${type}\nData: ${data}`);
    // Use barcode data to lookup item in inventory
    lookupItemByBarcode(data);
  };

  const lookupItemByBarcode = async (barcode: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/inventory/barcode/${barcode}`);
      if (response.data) {
        // Populate form with item data
        setTitle(response.data.title);
        setStorageLocation(response.data.storage_location);
        setPhotos(response.data.photos || []);
        Alert.alert('Item Found', `Found: ${response.data.title}`);
      }
    } catch (error) {
      Alert.alert('Not Found', 'No item found with this barcode');
    }
  };

  // CSV Download
  const downloadCSV = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/inventory/export-csv`);
      const csvContent = response.data;

      const filename = `inventory_${new Date().toISOString().split('T')[0]}.csv`;
      const fileUri = FileSystem.documentDirectory + filename;

      await FileSystem.writeAsStringAsync(fileUri, csvContent, {
        encoding: FileSystem.EncodingType.UTF8,
      });

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri);
      } else {
        Alert.alert('Success', `CSV saved to: ${fileUri}`);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to download CSV');
    }
  };

  // Template Management
  const saveAsTemplate = async () => {
    if (!title.trim()) {
      Alert.alert('Error', 'Title is required to save template');
      return;
    }

    const templateName = await new Promise<string>((resolve) => {
      Alert.prompt(
        'Template Name',
        'Enter a name for this template:',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Save', onPress: resolve },
        ]
      );
    });

    if (templateName) {
      const template: ListingTemplate = {
        id: Date.now().toString(),
        name: templateName,
        title,
        description,
        brand,
        size,
        color,
        condition,
      };

      setTemplates([...templates, template]);
      Alert.alert('Success', 'Template saved!');
    }
  };

  const loadTemplate = (template: ListingTemplate) => {
    setTitle(template.title);
    setDescription(template.description);
    setBrand(template.brand || '');
    setSize(template.size || '');
    setColor(template.color || '');
    setCondition(template.condition);
    setShowTemplates(false);
    Alert.alert('Template Loaded', `Loaded: ${template.name}`);
  };

  const copyToClipboard = async (text: string) => {
    await Clipboard.setStringAsync(text);
    Alert.alert('Copied', 'Text copied to clipboard');
  };

  // Inventory Management
  const loadInventory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/inventory`);
      setInventory(response.data);
    } catch (error) {
      Alert.alert('Error', 'Failed to load inventory');
    }
  };

  const addToInventory = async () => {
    if (!title.trim() || !storageLocation.trim()) {
      Alert.alert('Error', 'Title and storage location are required');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/inventory`, {
        title,
        storage_location: storageLocation,
        photos: photos.map(p => ({ photo_id: p.photo_id, url: p.url })),
      });

      setInventory([...inventory, response.data]);
      Alert.alert('Success', 'Added to inventory!');
    } catch (error) {
      Alert.alert('Error', 'Failed to add to inventory');
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

        {/* Navigation Buttons */}
        <View style={styles.navButtons}>
          <TouchableOpacity
            style={[styles.navButton, currentScreen === 'camera' && styles.navButtonActive]}
            onPress={() => setCurrentScreen('camera')}>
            <Text style={styles.navButtonText}>📷 Camera</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.navButton, currentScreen === 'inventory' && styles.navButtonActive]}
            onPress={() => {
              setCurrentScreen('inventory');
              loadInventory();
            }}>
            <Text style={styles.navButtonText}>📦 Inventory</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.navButton, currentScreen === 'templates' && styles.navButtonActive]}
            onPress={() => setCurrentScreen('templates')}>
            <Text style={styles.navButtonText}>📋 Templates</Text>
          </TouchableOpacity>
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

            <TouchableOpacity
              style={[styles.actionButton, styles.barcodeButton]}
              onPress={async () => {
                const granted = await requestBarcodePermission();
                if (granted) {
                  setShowBarcodeScanner(true);
                } else {
                  Alert.alert('Permission Denied', 'Camera permission is required for barcode scanning');
                }
              }}>
              <Text style={styles.actionButtonText}>📱 Scan Barcode</Text>
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

        {/* Template and Utility Buttons */}
        <View style={styles.utilityButtons}>
          <TouchableOpacity
            style={[styles.utilityButton, styles.templateButton]}
            onPress={() => setShowTemplates(true)}>
            <Text style={styles.utilityButtonText}>📋 Templates</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.utilityButton, styles.csvButton]}
            onPress={downloadCSV}>
            <Text style={styles.utilityButtonText}>📊 Download CSV</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.utilityButton, styles.inventoryButton]}
            onPress={() => setShowInventory(true)}>
            <Text style={styles.utilityButtonText}>📦 Inventory</Text>
          </TouchableOpacity>
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

      {/* Barcode Scanner Modal */}
      <Modal visible={showBarcodeScanner} animationType="slide">
        <View style={styles.modalContainer}>
          <BarCodeScanner
            onBarCodeScanned={handleBarCodeScanned}
            style={StyleSheet.absoluteFillObject}
          />
          <View style={styles.barcodeOverlay}>
            <Text style={styles.barcodeText}>Scan Barcode</Text>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowBarcodeScanner(false)}>
              <Text style={styles.closeButtonText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Inventory Modal */}
      <Modal visible={showInventory} animationType="slide">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>📦 Inventory</Text>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowInventory(false)}>
              <Text style={styles.closeButtonText}>×</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            data={inventory}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <View style={styles.inventoryItem}>
                <Text style={styles.inventoryTitle}>{item.title}</Text>
                <Text style={styles.inventoryLocation}>{item.storage_location}</Text>
                <Text style={styles.inventoryDate}>
                  {new Date(item.created_at).toLocaleDateString()}
                </Text>
              </View>
            )}
            ListEmptyComponent={<Text style={styles.emptyText}>No items in inventory</Text>}
          />
          <TouchableOpacity style={styles.addToInventoryButton} onPress={addToInventory}>
            <Text style={styles.addToInventoryText}>Add Current Item to Inventory</Text>
          </TouchableOpacity>
        </View>
      </Modal>

      {/* Templates Modal */}
      <Modal visible={showTemplates} animationType="slide">
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>📋 Templates</Text>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowTemplates(false)}>
              <Text style={styles.closeButtonText}>×</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            data={templates}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.templateItem}
                onPress={() => loadTemplate(item)}>
                <Text style={styles.templateName}>{item.name}</Text>
                <Text style={styles.templatePreview}>{item.title}</Text>
              </TouchableOpacity>
            )}
            ListEmptyComponent={<Text style={styles.emptyText}>No templates saved</Text>}
          />
          <TouchableOpacity style={styles.saveTemplateButton} onPress={saveAsTemplate}>
            <Text style={styles.saveTemplateText}>Save Current as Template</Text>
          </TouchableOpacity>
        </View>
      </Modal>
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

  // New mobile feature styles
  navButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#2a2a2a',
  },
  navButton: {
    flex: 1,
    padding: 10,
    marginHorizontal: 5,
    borderRadius: 8,
    backgroundColor: '#3a3a3a',
    alignItems: 'center',
  },
  navButtonActive: {
    backgroundColor: '#4CAF50',
  },
  navButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  barcodeButton: {
    backgroundColor: '#FF6B35',
  },
  utilityButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  utilityButton: {
    flex: 1,
    padding: 12,
    marginHorizontal: 5,
    borderRadius: 8,
    alignItems: 'center',
  },
  templateButton: {
    backgroundColor: '#9C27B0',
  },
  csvButton: {
    backgroundColor: '#2196F3',
  },
  inventoryButton: {
    backgroundColor: '#FF9800',
  },
  utilityButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  modalTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  closeButton: {
    padding: 10,
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 18,
  },
  barcodeOverlay: {
    position: 'absolute',
    top: 50,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  barcodeText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    backgroundColor: 'rgba(0,0,0,0.7)',
    padding: 10,
    borderRadius: 8,
  },
  inventoryItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  inventoryTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  inventoryLocation: {
    color: '#ccc',
    fontSize: 14,
  },
  inventoryDate: {
    color: '#999',
    fontSize: 12,
  },
  templateItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  templateName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  templatePreview: {
    color: '#ccc',
    fontSize: 14,
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    padding: 20,
    fontSize: 16,
  },
  addToInventoryButton: {
    backgroundColor: '#4CAF50',
    padding: 15,
    margin: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  addToInventoryText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  saveTemplateButton: {
    backgroundColor: '#9C27B0',
    padding: 15,
    margin: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveTemplateText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
