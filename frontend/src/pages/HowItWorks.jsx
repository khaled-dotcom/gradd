import { Link } from 'react-router-dom';
import { Briefcase, FileText, RefreshCw, Shield } from 'lucide-react';

const HowItWorks = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
          كيف يعمل EmpowerWork؟
        </h1>

        <div className="space-y-6">
          <section className="card">
            <div className="flex gap-3">
              <Briefcase className="h-6 w-6 text-accent shrink-0" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  عرض الوظائف
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  نجمع إعلانات وظائف تقنية من مصادر عامة (مثل Wuzzuf وForasna وLinkedIn) لعرضها
                  في مكان واحد مع فلترة لمصر ومجال البرمجة. المصدر يظهر للشفافية فقط.
                </p>
              </div>
            </div>
          </section>

          <section className="card">
            <div className="flex gap-3">
              <FileText className="h-6 w-6 text-accent shrink-0" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  التقديم على موقعنا فقط
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  عند الضغط على «Apply on EmpowerWork» ترفع سيرتك الذاتية أو تدخل بياناتك هنا.
                  طلبك يُحفظ في نظامنا ويراجعه المسؤول — لا نُحوّلك لتقديم خارجي على مواقع
                  التوظيف.
                </p>
              </div>
            </div>
          </section>

          <section className="card">
            <div className="flex gap-3">
              <RefreshCw className="h-6 w-6 text-accent shrink-0" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  تحديث القائمة
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  تُحدَّث الوظائف تلقائياً كل 8 ساعات عبر نظام البيانات (Airflow). يمكن
                  للمسؤول تشغيل استيراد يدوي من لوحة التحكم عند الحاجة.
                </p>
              </div>
            </div>
          </section>

          <section className="card">
            <div className="flex gap-3">
              <Shield className="h-6 w-6 text-accent shrink-0" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  خصوصيتك
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  بيانات التقديم والسيرة الذاتية تبقى على خوادم EmpowerWork ولا تُرسل
                  تلقائياً لأصحاب العمل الخارجيين إلا بموافقتك عبر مراجعة الإدارة.
                </p>
              </div>
            </div>
          </section>
        </div>

        <div className="mt-8 flex gap-4">
          <Link to="/" className="btn-primary">
            تصفح الوظائف
          </Link>
          <Link to="/register" className="btn-secondary">
            إنشاء حساب
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HowItWorks;
