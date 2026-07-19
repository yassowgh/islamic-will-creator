/// Domain models shared across the app.
enum Madhhab { hanafi, maliki, shafii, hanbali, jafari }

extension MadhhabX on Madhhab {
  String get label => switch (this) {
        Madhhab.hanafi => 'Hanafi (Sunni)',
        Madhhab.maliki => 'Maliki (Sunni)',
        Madhhab.shafii => "Shafi'i (Sunni)",
        Madhhab.hanbali => 'Hanbali (Sunni)',
        Madhhab.jafari => "Ja'fari (Shia)",
      };
  String get explainer => switch (this) {
        Madhhab.hanafi => 'Grandfather excludes siblings.',
        Madhhab.maliki => 'Grandfather shares with siblings (best-of).',
        Madhhab.shafii => 'Grandfather shares; mushtaraka applied.',
        Madhhab.hanbali => 'Close to Shafi\'i; no mushtaraka.',
        Madhhab.jafari => 'Class system; no awl; spouse always inherits.',
      };
}

/// Relationship keys must match the backend engine exactly.
const kRelationships = [
  'husband', 'wife', 'son', 'daughter', 'sons_son', 'sons_daughter',
  'father', 'mother', 'paternal_grandfather', 'paternal_grandmother',
  'maternal_grandmother', 'full_brother', 'full_sister',
  'paternal_brother', 'paternal_sister', 'maternal_brother',
  'maternal_sister', 'full_brothers_son', 'paternal_brothers_son',
  'full_paternal_uncle', 'paternal_paternal_uncle', 'full_uncles_son',
  'paternal_uncles_son',
];

class HeirEntry {
  HeirEntry({required this.relationship, this.count = 1,
      this.isMuslim = true, this.causedDeath = false, this.name = ''});
  final String relationship;
  int count;
  bool isMuslim;
  bool causedDeath;
  String name;

  Map<String, dynamic> toJson() => {
        'relationship': relationship, 'count': count,
        'isMuslim': isMuslim, 'causedDeath': causedDeath,
      };
}

class Person {
  Person({this.name = '', this.address = '', this.occupation = ''});
  String name;
  String address;
  String occupation;
}

enum WillStatus {
  initiated, finalized, downloaded, inSignature,
  signedUploaded, signedUploadedVerified,
}

class WillDraft {
  WillDraft();
  String fullLegalName = '';
  String address = '';
  DateTime? dateOfBirth;
  Madhhab madhhab = Madhhab.hanafi;
  String assetsScope = 'all_uk';
  double grossEstate = 0, funeralCosts = 0, debts = 0, unpaidMahr = 0,
      unpaidZakat = 0, kaffarat = 0, fidya = 0;
  double wasiyyaPercent = 0; // hard-capped at 33.33 in the UI and backend
  String wasiyyaRecipients = '';
  Person executor = Person();
  Person backupExecutor = Person();
  Person witness1 = Person();
  Person witness2 = Person();
  String guardian = '';
  String funeralWishes =
      'Islamic burial without unnecessary delay; ghusl and janazah '
      'prayer; no cremation.';
  final Map<String, HeirEntry> heirs = {};
  WillStatus status = WillStatus.initiated;

  void setHeirCount(String relationship, int count) {
    if (count <= 0) {
      heirs.remove(relationship);
    } else {
      heirs.putIfAbsent(relationship,
          () => HeirEntry(relationship: relationship)).count = count;
    }
  }

  int heirCount(String relationship) => heirs[relationship]?.count ?? 0;

  /// Wills Act 1837 s.15 check: a witness must not share a name with any
  /// named beneficiary (heuristic; the full check is confirmed manually).
  List<String> witnessConflicts() {
    final names = heirs.values.map((h) => h.name.trim().toLowerCase())
        .where((n) => n.isNotEmpty).toSet();
    final conflicts = <String>[];
    for (final w in [witness1, witness2]) {
      if (names.contains(w.name.trim().toLowerCase()) &&
          w.name.trim().isNotEmpty) {
        conflicts.add(w.name);
      }
    }
    return conflicts;
  }
}

class ShareRow {
  ShareRow({required this.relationship, required this.count,
      required this.fraction, required this.percentage,
      required this.reason});
  final String relationship;
  final int count;
  final String fraction;
  final double percentage;
  final String reason;
}

class CalcResult {
  CalcResult({required this.madhhab, required this.rows,
      required this.blocked, required this.notes, required this.warnings,
      required this.awlApplied, required this.raddApplied,
      required this.engineVersion, this.distributableGbp});
  final String madhhab;
  final List<ShareRow> rows;
  final List<Map<String, dynamic>> blocked;
  final List<String> notes;
  final List<String> warnings;
  final bool awlApplied;
  final bool raddApplied;
  final String engineVersion;
  final double? distributableGbp;

  factory CalcResult.fromJson(Map<String, dynamic> j) => CalcResult(
        madhhab: j['madhhab'] as String,
        engineVersion: j['engineVersion'] as String? ?? '?',
        awlApplied: j['awlApplied'] as bool? ?? false,
        raddApplied: j['raddApplied'] as bool? ?? false,
        notes: List<String>.from(j['notes'] ?? const []),
        warnings: List<String>.from(j['warnings'] ?? const []),
        blocked: List<Map<String, dynamic>>.from(j['blocked'] ?? const []),
        distributableGbp:
            (j['estate']?['distributable'] as num?)?.toDouble(),
        rows: [
          for (final r in (j['sharesTable'] as List? ?? const []))
            ShareRow(
              relationship: r['relationship'] as String,
              count: r['count'] as int? ?? 1,
              fraction: r['fraction'] as String,
              percentage: (r['percentage'] as num).toDouble(),
              reason: r['reason'] as String? ?? '',
            ),
        ],
      );
}

String prettyRel(String r) {
  final s = r.replaceAll('_', ' ');
  return s[0].toUpperCase() + s.substring(1);
}
