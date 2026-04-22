# Gusanitos Arena

El juego **Gusanitos Arena** es básicamente una versión propia de los juegos tipo **Slither.io** o **Snake.io**, donde controlás una serpiente dentro de un mapa grande lleno de comida y otros jugadores.

## Idea principal

El jugador controla un **gusanito (una serpiente)** que se mueve continuamente dentro de un mundo circular.

El objetivo es **crecer lo más posible** comiendo comida que aparece por el mapa.  
Cada pedacito de comida hace que la serpiente gane segmentos, es decir, que se vuelva más larga.

## Bots y enemigos

No estás solo en el mapa.

También hay **bots (serpientes controladas por inteligencia artificial)** que hacen lo mismo que vos:

- Buscan comida
- Escapan de amenazas
- A veces intentan cazar serpientes más pequeñas

## Mecánica principal

La mecánica central del juego es la misma que en los clásicos juegos de serpientes competitivos:

> Si la **cabeza de tu serpiente choca contra el cuerpo de otra**, tu serpiente muere.

Cuando esto ocurre, todos los segmentos que tenía se convierten en comida que queda en el suelo para que otros jugadores la recojan.

Por eso el juego mezcla dos ideas principales:

- **Crecer comiendo comida**
- **Sobrevivir evitando chocar con otras serpientes**

## Mecánica de Boost

Existe una mecánica llamada **boost**.

Cuando activás el boost:

- La serpiente se mueve más rápido
- Sirve para **escapar o atacar**

Pero tiene un costo:

- La serpiente **pierde segmentos mientras acelera**

Es decir, estás literalmente **sacrificando tamaño para ganar velocidad**.

## El mapa

El mapa es **un círculo enorme**.

Si la serpiente se acerca demasiado al borde y lo toca, **muere inmediatamente**.  
Esto evita que los jugadores se escapen indefinidamente y mantiene la acción concentrada en el centro del mapa.

## Sistemas visuales y HUD

El juego incluye varios elementos de interfaz para ayudar al jugador:

- **Minimapa** que muestra la posición de las serpientes
- **Leaderboard** con los jugadores más largos
- **Contador de score**
- **Contador de kills**
- **Tiempo de supervivencia**
- **Barra de boost**
- **Minimapa del mundo**

## Modo multijugador local

El juego también incluye **modo multijugador en la misma pantalla**.

En este modo la pantalla se divide en dos:

- **Jugador 1:** usa el mouse para moverse  
- **Jugador 2:** usa **WASD** para controlar su serpiente

## Resumen

**Gusanitos Arena** es un juego de **supervivencia y crecimiento** donde el objetivo es convertirse en la serpiente más grande del mapa.

El jugador debe:

- Comer comida para crecer
- Evitar chocar con otras serpientes
- Usar boost para moverse más rápido
- Intentar convertirse en **la serpiente más larga del mapa**

## Proceso de desarrollo del juego

Cuando comencé a desarrollar el código, fui creando cada función poco a poco. Durante ese proceso aparecieron muchos errores, por ejemplo botones que no funcionaban o que directamente generaban errores al ejecutarse. 

Muchos de estos problemas se debían a cuestiones simples, como el orden en el que se llamaban las funciones o cómo estaban organizadas ciertas partes del código. Estos errores alteraban el funcionamiento del juego al momento de ejecutarlo. Para resolver varios de ellos utilicé ayuda de inteligencia artificial, lo que me permitió identificar más rápido dónde estaba el problema.

Una vez que el juego comenzó a tomar forma, empecé a agregar distintos elementos que estaban incluidos en la consigna, como el modo multijugador. Esta parte resultó ser una de las más complicadas, ya que sincronizar el movimiento de ambos jugadores, manejar los mapas individuales, el ranking y el sistema de puntaje generó muchos errores inesperados. Aunque estos sistemas parecen simples en teoría, fueron los que más tiempo me llevaron debido a la cantidad de problemas que surgían al implementarlos.

Cuando el juego ya estaba casi terminado, sentí que el resultado final no terminaba de convencerme. Por eso decidí realizar algunos cambios importantes para mejorarlo. Eliminé todas las imágenes que había utilizado anteriormente, tanto en el fondo como en el menú, y opté por generar esos elementos directamente mediante código. Supuse que de esa forma el juego sería más fluido y visualmente más consistente, y finalmente funcionó mejor de lo esperado.

Luego agregué colores a los orbes para hacer el entorno más dinámico y realicé un cambio importante en la estructura del mapa: pasé de un mapa cuadrado a un mapa circular, similar al del juego original. También mejoré el diseño de los gusanitos, agregando más detalles visuales.

Por último, trabajé en optimizar el rendimiento y la fluidez del juego, ajustando aspectos como los FPS, el movimiento de las serpientes y la forma en que se actualiza el mapa. Esta fue una de las partes que más tiempo me llevó, pero finalmente logré mejorar considerablemente el funcionamiento general.

Aunque no fue un proceso fácil y hubo muchos momentos de frustración, pude llegar a un resultado final que me dejó bastante conforme.