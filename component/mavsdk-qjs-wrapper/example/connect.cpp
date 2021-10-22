#include "../include/mavsdk_wrapper.h"

int main() {
  start("udp://169.79.1.1:7909", "mavsdk-log", 30);
}