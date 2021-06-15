from imutils.object_detection import non_max_suppression
import numpy as np
import pytesseract
import argparse
import cv2


def decode_predictions(scores, geometry):
  (numRows, numCols) = scores.shape[2:4]
  rects = []
  confidences = []

  for y in range(0, numRows):
    scoresData = scores[0, 0, y]
    xData0 = geometry[0, 0, y]
    xData1 = geometry[0, 1, y]
    xData2 = geometry[0, 2, y]
    xData3 = geometry[0, 3, y]
    anglesData = geometry[0, 4, y]

    for x in range(0, numCols):
      if scoresData[x] < args["min_confidence"]:
        continue
      
      (offsetX, offsetY) = (x * 4.0, y * 4.0)

      angle = anglesData[x]
      cos = np.cos(angle)
      sin = np.sin(angle)

      h = xData0[x] + xData2[x]
      w = xData1[x] + xData3[x]

      endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
      endY = int(offsetY + (cos * xData2[x]) - (sin * xData1[x]))          
      startX = int(endX - w)
      startY = int(endY - h)

      rects.append((startX, startY, endX, endY))
      confidences.append(scoresData[x])

  return (rects, confidences)

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", type=str, help="path to input image")
ap.add_argument("-east", "--east", type=str, help="path to input EAST text detector")
ap.add_argument("-c", "--min-confidence", type=float, default=0.5, help="minimum probability required to inspect a region")
ap.add_argument("-w", "--width", type=int, default=320, help="nearest multiple of 32 for resized width")
ap.add_argument("-e", "--height", type=int, default=320, help="nearest multiple of 32 for resized height")           
ap.add_argument("-p", "--padding", type=float, default=0.0, help="amount of padding to add to each border")
args = vars(ap.parse_args())

image = cv2.imread(args["image"])
orig = image.copy()
(H, W) = image.shape[:2]

(newW, newH) = (args["width"],args["height"])
rW = W / float(newW)
rH = H / float(newH)

image = cv2.resize(image, (newW, newH))
(H, W) = image.shape[:2]

layerNames = ["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"]

print("[INFO] loading EAST text detector...")
net = cv2.dnn.readNet(args["east"])

blob = cv2.dnn.blobFromImage(image, 1.0, (W, H), (123.68, 116.78, 103.94), swapRB=True, crop=False)
net.setInput(blob)
(scores, geometry) = net.forward(layerNames)

(rects, confidences) = decode_predictions(scores, geometry)
boxes = non_max_suppression(np.array(rects), probs=confidences)

results = []

for (startX, startY, endX, endY) in boxes:
  startX = int(startX * rW)
  startY = int(startY * rH)
  endX = int(endX * rW)
  endY = int(endY * rH)

  dX = int((endX - startX) * args["padding"])
  dY = int((endY - startY) * args["padding"])

  startX = max(0, startX - dX)
  startY = max(0, startY - dY) 
  endX = min(W, endX, + (dX * 2))
  endY = min(H, endY, + (dY * 2))

  roi = orig[startY:endY, startX:endX]
  text = pytesseract.image_to_string(roi, config= ("-1 eng --oem 1 --psm 7"))
  

  results.append(((startX, startY, endX, endY),text))

results = sorted(results, key=lambda r:r[0][1])

for ((startX, startY, endX, endY), test) in results:
  print("{}\n".format(text))
  
  text = "".join([c if ord(c) < 128 else "" for c in test]).strip()
  output = orig.copy()
  cv2.rectangle(output, (startX, startY), (endX, endY), (0, 0, 255), 2)
  cv2.putText(output, text, (startX, startY - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

  cv2.imshow("Text detection", output)
  cv2.waitkey(0)