# TF 0.25.24 코어 재빌드

현재 실행에 사용한 ARM64 바이너리는 home/nav2_follow_stabilization/goal3_success_tf02524/lib/libtf2.so에 보존했다.
Humble/아키텍처/ABI가 다른 장치에 그대로 사용하지 않는다.
원본 출처: https://github.com/ros2/geometry2/tree/0.25.24
재빌드는 별도 디렉터리에서 수행한다. 시스템 /opt/ros 파일을 덮어쓰지 않는다.

```bash
source /opt/ros/humble/setup.bash
cmake -S tf2_overlay_source -B /tmp/goal3_tf2_rebuild
cmake --build /tmp/goal3_tf2_rebuild -j2
```

재빌드한 파일은 컴파일 환경에 따라 해시가 달라질 수 있다. 기존 검증 manifest를 무조건 갱신하지 않는다.
validated_build.json과 verify_overlay.py는 원래 검증했던 build/ 산출물까지 참조하는 기록이다.
이 소스 백업에서는 해당 build/ 전체를 제외했으므로 verify_overlay.py를 그대로 실행해 통과한다고 주장하지 않는다.
원본 upstream 라이선스는 함께 보존한 LICENSE 파일을 따른다.
