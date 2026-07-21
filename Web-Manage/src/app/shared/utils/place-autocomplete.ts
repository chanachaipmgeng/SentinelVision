/** Mount Google PlaceAutocompleteElement and resolve selected place location. */

export type PlacePickResult = {
  lat: number;
  lng: number;
  name?: string;
  address?: string;
};

type GmpSelectEvent = Event & {
  placePrediction?: google.maps.places.PlacePrediction;
  place?: google.maps.places.Place;
};

export async function mountPlaceAutocomplete(
  host: HTMLElement,
  onPick: (result: PlacePickResult) => void
): Promise<google.maps.places.PlaceAutocompleteElement | null> {
  if (!host || typeof google === 'undefined' || !google.maps?.importLibrary) {
    console.error('Google Maps Places library is not available');
    return null;
  }

  host.replaceChildren();

  await google.maps.importLibrary('places');
  const placeAutocomplete = new google.maps.places.PlaceAutocompleteElement({});
  placeAutocomplete.style.width = '100%';
  placeAutocomplete.style.display = 'block';
  host.appendChild(placeAutocomplete);

  placeAutocomplete.addEventListener('gmp-select', async (event) => {
    const selectEvent = event as GmpSelectEvent;
    let place = selectEvent.place;

    if (!place && selectEvent.placePrediction) {
      place = selectEvent.placePrediction.toPlace();
    }
    if (!place) {
      return;
    }

    await place.fetchFields({
      fields: ['displayName', 'formattedAddress', 'location'],
    });

    const location = place.location;
    if (!location) {
      return;
    }

    onPick({
      lat: location.lat(),
      lng: location.lng(),
      name: place.displayName ?? undefined,
      address: place.formattedAddress ?? undefined,
    });
  });

  return placeAutocomplete;
}
