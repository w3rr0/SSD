# Popularity bias w rekomendacjach muzyki

## Problem

Platformy streamingowe układają kolejkę odtwarzania i rekomendacje na podstawie tego, co użytkownicy już słuchają. Algorytmy uczone na odsłuchaniach faworyzują utwory popularne, bo mają one najwięcej danych. Popularni artyści zyskują jeszcze więcej odsłuchań, a nowi artyści rzadko trafiają do rekomendacji. Efekt nazywa się popularity bias.

Problem nie polega tylko na jednej decyzji algorytmu, lecz na pętli sprzężenia zwrotnego: rekomendacja zmienia odsłuchania, odsłuchania zmieniają dane, a dane zmieniają kolejne rekomendacje. Taki proces dobrze badać symulacją, bo rzeczywiste platformy nie pozwalają testować polityk bez wpływu na prawdziwych ludzi.

## Konkretne pytanie badawcze

> Czy rekomender z kontrolowaną eksploracją potrafi znacząco poprawić odsłuchania nowych artystów, nie obniżając czasu słuchania i satysfakcji użytkowników?

## Zakres modelu

### Elementy

- **Słuchacz (agent)** — profil gustu (wektor preferencji), skłonność do eksploracji, tolerancja na nieznane utwory, czas dziennego słuchania.
- **Utwór i artysta** — cechy (gatunek, wektor cech), popularność początkowa, wiek w katalogu.
- **Rekomender** — wybiera kolejne utwory do kolejki lub strony głównej.
- **Uwaga** — ograniczona liczba utworów, które słuchacz może przesłuchać w ciągu dnia.
- **Ekonomia artystów** — liczba odsłuchań jako przychód, próg, od którego artysta pozostaje na platformie.

### Zdarzenia dyskretne

- rozpoczęcie sesji słuchania,
- wyświetlenie rekomendacji lub kolejki,
- odtworzenie, pominięcie, polubienie lub zapisanie utworu,
- zakończenie sesji,
- aktualizacja modelu rekomendera (np. raz na dobę),
- pojawienie się nowego utworu lub artysty w katalogu,
- rezygnacja artysty z platformy.

### Stan agenta

`bez sesji -> w sesji -> słucha -> pomija -> zapisuje -> koniec sesji`. Prawdopodobieństwo pominięcia zależy od dopasowania utworu do gustu oraz od tolerancji na nowość.

## Strategie do porównania

1. **Losowa** — utwory wybierane losowo z katalogu.
2. **Najpopularniejsze** — ranking wg liczby odsłuchań.
3. **Filtrowanie kolaboratywne** — podobieństwo użytkowników lub utworów (np. faktoryzacja macierzy).
4. **Z karą za popularność** — wynik rekomendacji zmniejszany dla bardzo popularnych utworów.
5. **Eksploracja** — pewien odsetek miejsc w kolejce zarezerwowany dla nowych lub rzadko słuchanych utworów (np. epsilon-greedy lub bandyta kontekstowy).
6. **Strategia ucząca się** — agent ML optymalizujący kompromis między satysfakcją a różnorodnością.

## Dane i ich przygotowanie

Możliwe źródła:

- **Last.fm LFM-2b / LFM-1b** — zbiory odsłuchań użytkowników z cechami; sprawdzić aktualną dostępność i licencję przed użyciem,
- **Million Playlist Dataset** (Spotify, RecSys Challenge 2018) — milion playlist z utworami; sprawdzić, czy zbiór jest nadal dostępny,
- **Spotify Charts i Billboard** — dane o popularności w czasie,
- **MusicBrainz** — metadane artystów i gatunków.

Przygotowanie danych:

1. wybrać podzbiór (np. kilka tysięcy użytkowników i kilkadziesiąt tysięcy utworów),
2. zbudować macierz użytkownik–utwór i policzyć rozkład popularności (spodziewany długi ogon),
3. wyznaczyć wektory gustu i cech utworów (np. faktoryzacja macierzy lub embeddingi),
4. oszacować rozkłady długości sesji, odsetka pominięć i skłonności do eksploracji,
5. podzielić historię na część do kalibracji i część testową,
6. porównać rozkład popularności z symulacji z rozkładem rzeczywistym.

Prawdziwe odsłuchania nie mówią, co użytkownik by polubił, gdyby mu to pokazano. Dlatego model preferencji agentów jest założeniem i wymaga analizy wrażliwości.

## Teza i metryki

**Teza:** rekomender z umiarkowaną eksploracją (np. 10–20% kolejki) zwiększa odsłuchania nowych artystów kilkukrotnie, a czas słuchania obniża tylko nieznacznie; przy zbyt dużej eksploracji satysfakcja słuchaczy spada.

Metryki:

- średni czas słuchania i odsetek pominięć,
- współczynnik Gini rozkładu odsłuchań między artystami,
- odsetek odsłuchań należących do nowych artystów (np. młodszych niż rok),
- liczba artystów powyżej progu opłacalności,
- różnorodność kolejki (liczba gatunków i artystów),
- stabilność w czasie po wielu cyklach sprzężenia zwrotnego.

Eksperymenty: różny udział eksploracji, różne tolerancje słuchaczy na nowość, początek z rozkładem rzeczywistym lub wyrównanym, długie symulacje (miesiące czasu symulowanego) w celu zobaczenia efektu pętli sprzężenia.

## Środowisko

Python. Silnik zdarzeń własny (`heapq`), `pandas` i `numpy` do danych, `scipy` lub `scikit-learn` do faktoryzacji i modeli preferencji, `matplotlib` do wykresów. Rekomender wymienny jak plugin, żeby strategie można było porównywać bez zmian w symulatorze. Agenci słuchacze mogą korzystać z modeli ML wytrenowanych na danych (część "nice to have" z `ideas.md`).

Źródła:

- [Last.fm LFM-2b](http://www.cp.jku.at/datasets/LFM-2b/),
- [Million Playlist Dataset](https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge),
- [MusicBrainz](https://musicbrainz.org/).
