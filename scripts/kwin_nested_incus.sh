#!/usr/bin/env bash

SSH_ARGS="$1"
CONTAINER_NAME="$2"
PROJECT_PATH="$3"
WAYLAND_NAME="NestedWayland"
WAYLAND_SOCKET="$XDG_RUNTIME_DIR/wayland-nested"
XWAYLAND_NAME="NestedXWayland"
XWAYLAND_SOCKET="/tmp/.X11-unix/X1"

if [ -z "$SSH_ARGS" ]; then
  echo "No SSH arguments provided"
  exit 1
fi

if [ -z "$CONTAINER_NAME" ]; then
  echo "No Incus container name provided"
  exit 1
fi

if [ -z "$PROJECT_PATH" ]; then
  echo "No path to project root provided"
  exit 1
fi

if [[ "$PROJECT_PATH" != *"/" ]]; then
  PROJECT_PATH="$PROJECT_PATH/"
fi

add_device() {
  sudo incus config device add "$CONTAINER_NAME" "$1" proxy \
    listen=unix:$2 \
    connect=unix:$2 \
    bind=instance \
    gid=1000 \
    uid=1000 \
    mode=0660
}

remove_device() {
  sudo incus config device remove "$CONTAINER_NAME" "$1"
  sudo incus exec "$CONTAINER_NAME" -- rm "$2"
}

cleanup() {
  remove_device "$WAYLAND_NAME" "$WAYLAND_SOCKET"
  remove_device "$XWAYLAND_NAME" "$XWAYLAND_SOCKET"
  exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "Adding devices to Incus container..."

add_device "$WAYLAND_NAME" "$WAYLAND_SOCKET"
add_device "$XWAYLAND_NAME" "$XWAYLAND_SOCKET"

ssh -n "$SSH_ARGS" "cat \"$PROJECT_PATH\"scripts/kwin_nested_start.py" | python - "xhost +local:"

cleanup
