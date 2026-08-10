import 'package:flutter/material.dart';

class Sparkline extends StatelessWidget {
  const Sparkline({required this.values, required this.color, super.key});

  final List<double> values;
  final Color color;

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _SparklinePainter(values, color),
    size: const Size(80, 28),
  );
}

class _SparklinePainter extends CustomPainter {
  const _SparklinePainter(this.values, this.color);

  final List<double> values;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;
    final line = Path();
    for (var index = 0; index < values.length; index++) {
      final point = Offset(
        index * size.width / (values.length - 1),
        size.height * (1 - values[index]),
      );
      index == 0
          ? line.moveTo(point.dx, point.dy)
          : line.lineTo(point.dx, point.dy);
    }
    final fill = Path.from(line)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(
      fill,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: .32), color.withValues(alpha: 0)],
        ).createShader(Offset.zero & size),
    );
    canvas.drawPath(
      line,
      Paint()
        ..color = color
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke,
    );
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter oldDelegate) =>
      oldDelegate.values != values || oldDelegate.color != color;
}
