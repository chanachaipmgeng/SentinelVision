import { buildKioskWsUrl, WS_CONNECTING, WS_OPEN } from './kiosk-ws-url';

describe('kiosk-ws-url', () => {
  const loc = {
    protocol: 'https:',
    host: 'kiosk.example.com',
    origin: 'https://kiosk.example.com',
  };

  it('maps https origin to wss /face/ws/kiosk', () => {
    expect(buildKioskWsUrl('', loc)).toBe('wss://kiosk.example.com/face/ws/kiosk');
  });

  it('maps http origin to ws', () => {
    const httpLoc = {
      protocol: 'http:',
      host: 'localhost:4200',
      origin: 'http://localhost:4200',
    };
    expect(buildKioskWsUrl('', httpLoc)).toBe('ws://localhost:4200/face/ws/kiosk');
  });

  it('uses absolute baseUrl host when provided', () => {
    expect(buildKioskWsUrl('https://api.example.com', loc)).toBe(
      'wss://api.example.com/face/ws/kiosk',
    );
  });

  it('exposes pace.js-safe readyState literals', () => {
    expect(WS_CONNECTING).toBe(0);
    expect(WS_OPEN).toBe(1);
  });
});
