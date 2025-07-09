import cv2

def capture_image(filename="frame.jpg"):
    cap = cv2.VideoCapture(0)
    print("[📷 Press 's' to snap image]")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('s'):
            cv2.imwrite(filename, frame)
            break
    cap.release()
    cv2.destroyAllWindows()
    return filename
