import { Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { AlertsPage } from './pages/AlertsPage'
import { ArticleDetailPage } from './pages/ArticleDetailPage'
import { ArticlesPage } from './pages/ArticlesPage'
import { CustomersPage } from './pages/CustomersPage'
import { HomePage } from './pages/HomePage'
import { InventoriesPage } from './pages/InventoriesPage'
import { InventoryDetailPage } from './pages/InventoryDetailPage'
import { LoginPage } from './pages/LoginPage'
import { FefoPage } from './pages/FefoPage'
import { LotDetailPage } from './pages/LotDetailPage'
import { LotsPage } from './pages/LotsPage'
import { StockPage } from './pages/StockPage'
import { RecallDetailPage, RecallsPage } from './pages/RecallsPage'
import { RecallSimulationPage } from './pages/RecallSimulationPage'
import { TraceabilityPage } from './pages/TraceabilityPage'
import { DeclarationPage } from './pages/DeclarationPage'
import { PlanningPage } from './pages/PlanningPage'
import { ProductionOrderDetailPage } from './pages/ProductionOrderDetailPage'
import { ProductionOrderFormPage } from './pages/ProductionOrderFormPage'
import { ProductionOrdersPage } from './pages/ProductionOrdersPage'
import { EdiPage } from './pages/EdiPage'
import { SalePricesPage } from './pages/SalePricesPage'
import { SalesOrderDetailPage } from './pages/SalesOrderDetailPage'
import { SalesOrderFormPage } from './pages/SalesOrderFormPage'
import { SalesOrdersPage } from './pages/SalesOrdersPage'
import { PreparationPage } from './pages/PreparationPage'
import { ServiceRatePage } from './pages/ServiceRatePage'
import { ShipmentDetailPage, ShipmentsPage } from './pages/ShipmentsPage'
import { PurchaseOrderDetailPage } from './pages/PurchaseOrderDetailPage'
import { PurchaseOrderFormPage } from './pages/PurchaseOrderFormPage'
import { PurchaseOrdersPage } from './pages/PurchaseOrdersPage'
import { ReceptionFormPage } from './pages/ReceptionFormPage'
import { SitesPage } from './pages/SitesPage'
import { SuppliersPage } from './pages/SuppliersPage'
import { TemperaturesPage } from './pages/TemperaturesPage'

/** Les adresses de l'application. Toutes, sauf /connexion, exigent d'être connecté. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/connexion" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="articles" element={<ArticlesPage />} />
        <Route path="articles/:id" element={<ArticleDetailPage />} />
        <Route path="fournisseurs" element={<SuppliersPage />} />
        <Route path="clients" element={<CustomersPage />} />
        <Route path="sites" element={<SitesPage />} />
        <Route path="commandes" element={<PurchaseOrdersPage />} />
        <Route path="commandes/nouvelle" element={<PurchaseOrderFormPage />} />
        <Route path="commandes/:id" element={<PurchaseOrderDetailPage />} />
        <Route path="commandes/:id/reception" element={<ReceptionFormPage />} />
        <Route path="lots" element={<LotsPage />} />
        <Route path="lots/:id" element={<LotDetailPage />} />
        <Route path="stocks" element={<StockPage />} />
        <Route path="fefo" element={<FefoPage />} />
        <Route path="temperatures" element={<TemperaturesPage />} />
        <Route path="inventaires" element={<InventoriesPage />} />
        <Route path="inventaires/:id" element={<InventoryDetailPage />} />
        <Route path="alertes" element={<AlertsPage />} />
        <Route path="tracabilite" element={<TraceabilityPage />} />
        <Route path="rappels" element={<RecallsPage />} />
        <Route path="rappels/simulation" element={<RecallSimulationPage />} />
        <Route path="rappels/:id" element={<RecallDetailPage />} />
        <Route path="production" element={<ProductionOrdersPage />} />
        <Route path="production/nouveau" element={<ProductionOrderFormPage />} />
        <Route path="production/:id" element={<ProductionOrderDetailPage />} />
        <Route path="production/:id/declaration" element={<DeclarationPage />} />
        <Route path="planning" element={<PlanningPage />} />
        <Route path="ventes" element={<SalesOrdersPage />} />
        <Route path="ventes/nouvelle" element={<SalesOrderFormPage />} />
        <Route path="ventes/:id" element={<SalesOrderDetailPage />} />
        <Route path="ventes/:id/preparation" element={<PreparationPage />} />
        <Route path="expeditions" element={<ShipmentsPage />} />
        <Route path="expeditions/:id" element={<ShipmentDetailPage />} />
        <Route path="taux-de-service" element={<ServiceRatePage />} />
        <Route path="edi" element={<EdiPage />} />
        <Route path="tarifs-vente" element={<SalePricesPage />} />
        <Route path="*" element={<p>Page introuvable.</p>} />
      </Route>
    </Routes>
  )
}
