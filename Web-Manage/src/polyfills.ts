(window as unknown).global = window;
(window as unknown).process = {
  env: { DEBUG: undefined },
};