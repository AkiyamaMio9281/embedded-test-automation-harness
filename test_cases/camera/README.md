# Camera Tests

Camera HAL open and stream-start checks. Asserts no
`CameraService ... error` or `driver timeout` lines in logcat/dmesg
during the camera open window.

Driven by `CAM-001` in `test_plans/smoke.yaml`.
