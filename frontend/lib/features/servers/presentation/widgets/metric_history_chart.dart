import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../domain/entities/server.dart';

class MetricHistoryChart extends StatelessWidget {
  const MetricHistoryChart({required this.points, super.key});
  final List<MetricPoint> points;

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _MetricHistoryPainter(points),
    child: const SizedBox.expand(),
  );
}

class _MetricHistoryPainter extends CustomPainter {
  const _MetricHistoryPainter(this.points);
  final List<MetricPoint> points;

  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()..color = const Color(0xFF293244);
    for (var row = 1; row < 5; row++) {
      final y = size.height * row / 5;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    if (points.length < 2) return;
    final values = points.map((point) => point.value);
    final minimum = values.reduce(math.min);
    final maximum = values.reduce(math.max);
    final spread = maximum == minimum ? 1.0 : maximum - minimum;
    final path = Path();
    for (var index = 0; index < points.length; index++) {
      final x = index * size.width / (points.length - 1);
      final y =
          size.height -
          ((points[index].value - minimum) / spread * size.height);
      index == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = const Color(0xFF579CFF)
        ..strokeWidth = 2
        ..style = PaintingStyle.stroke,
    );
  }

  @override
  bool shouldRepaint(covariant _MetricHistoryPainter oldDelegate) =>
      oldDelegate.points != points;
}
