from transformers import ViTForImageClassification

MODEL_NAME = "buildborderless/CommunityForensics-DeepfakeDet-ViT"

model = ViTForImageClassification.from_pretrained(MODEL_NAME)

print("Model labels:")
print(model.config.id2label)

print()
print("Number of labels:")
print(model.config.num_labels)

print()
print("Classifier:")
print(model.classifier)